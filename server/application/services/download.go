package services

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
)

type DownloadsServiceParams struct {
	Cfg    config.DownloadsConfig
	Store  repositories.DownloadsRepository
	S3     repositories.S3SourceRepository
	Olap   repositories.OlapRepository
	Logger *logger.Logger
}

func NewDownloadsService(params DownloadsServiceParams) (*DownloadsService, error) {
	err := params.S3.Connect(context.Background())
	if err != nil {
		return nil, fmt.Errorf("error connecting to s3: %w", err)
	}
	return newDownloadService(params), nil
}

type DownloadsService struct {
	store  repositories.DownloadsRepository
	s3     repositories.S3SourceRepository
	olap   repositories.OlapRepository
	cfg    config.DownloadsConfig
	logger *logger.Logger
}

func newDownloadService(params DownloadsServiceParams) *DownloadsService {
	return &DownloadsService{
		store:  params.Store,
		s3:     params.S3,
		olap:   params.Olap,
		logger: params.Logger,
		cfg:    params.Cfg,
	}
}

type SSEEvent struct {
	DownloadID string `json:"download_id"`
	Type       string `json:"type"`
	Message    string `json:"message"`
}

func (s *DownloadsService) List(userID, orgID string, limit, offset int32) ([]*models.Download, error) {
	return s.store.ListDownloadsByUser(context.Background(), userID, orgID, limit, offset)
}

func (s *DownloadsService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.store.GetDownload(context.Background(), downloadID, orgID)
}

func (s *DownloadsService) Delete(downloadID, userID, orgID string) error {
	return s.store.DeleteDownload(context.Background(), downloadID, orgID)
}

func (s *DownloadsService) CreateDownloadAndStoreInS3(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
	ctx := context.Background()

	downloadJob, err := s.store.CreateDownload(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create download record: %w", err)
	}

	jobIDStr := downloadJob.ID.String()
	sseChan := make(chan models.DownloadsSSEData, 10)

	go func() {
		defer close(sseChan)

		jobCreatedPayload, _ := json.Marshal(downloadJob)
		jobCreatedMsg := fmt.Sprintf("event: job_created\ndata: %s\n\n", jobCreatedPayload)
		sseChan <- models.DownloadsSSEData{Data: []byte(jobCreatedMsg)}

		sendEvent := func(eventType, message string) {
			eventPayload := SSEEvent{
				DownloadID: jobIDStr,
				Type:       eventType,
				Message:    message,
			}
			payloadBytes, _ := json.Marshal(eventPayload)
			sseMessage := fmt.Sprintf("data: %s\n\n", payloadBytes)
			sseChan <- models.DownloadsSSEData{Data: []byte(sseMessage)}
		}

		handleFailure := func(failErr error) {
			errMsg := failErr.Error()
			failReq := &models.SetDownloadFailedRequest{ErrorMessage: errMsg}
			s.store.SetDownloadAsFailed(ctx, jobIDStr, failReq)

			errorPayload, _ := json.Marshal(map[string]string{"type": "error", "message": errMsg})
			errorMsg := fmt.Sprintf("event: error\ndata: %s\n\n", errorPayload)
			sseChan <- models.DownloadsSSEData{Data: []byte(errorMsg)}
		}

		if _, err := s.store.SetDownloadToProcessing(ctx, jobIDStr); err != nil {
			handleFailure(fmt.Errorf("failed to set job to processing: %w", err))
			return
		}
		sendEvent("status_update", "Processing query...")

		s3Key := fmt.Sprintf("%s/%s.%s", downloadJob.OrgID, jobIDStr, strings.ToLower(downloadJob.Format))
		sendEvent("status_update", "Executing data export to S3...")

		err = s.olap.ExecuteQueryAndStoreInS3(ctx, downloadJob.SQL, downloadJob.Format, fmt.Sprintf("s3://%s/%s", s.cfg.Bucket, s3Key))
		if err != nil {
			handleFailure(fmt.Errorf("data export to cloud storage failed: %w", err))
			return
		}

		sendEvent("status_update", "Generating secure download link...")
		expiresIn := 24 * time.Hour
		url, err := s.s3.GetPresignedURL(ctx, s3Key, expiresIn)
		if err != nil {
			handleFailure(fmt.Errorf("failed to generate download link: %w", err))
			return
		}

		completeReq := &models.SetDownloadCompletedRequest{
			PreSignedURL: url,
			ExpiresAt:    time.Now().Add(expiresIn),
		}
		if _, err = s.store.SetDownloadAsCompleted(ctx, jobIDStr, completeReq); err != nil {
			handleFailure(fmt.Errorf("failed to finalize job status: %w", err))
			return
		}

		sendEvent("complete", url)
	}()

	return sseChan, nil
}
