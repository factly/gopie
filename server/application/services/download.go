package services

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/download"
)

type DownloadsService interface {
	CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error)
	List(userID, orgID string, limit, offset int32) ([]*models.Download, error)
	Get(downloadID, userID, orgID string) (*models.Download, error)
	Delete(downloadID, userID, orgID string) error
}

type DownloadServerService struct {
	repo   repositories.DownloadServerRepository
	logger *logger.Logger
}

type DownloadsServiceParams struct {
	Cfg    config.DownloadsServerConfig
	Store  repositories.DownloadsRepository
	S3     repositories.S3SourceRepository
	Olap   repositories.OlapRepository
	Logger *logger.Logger
}

func NewDownloadsService(params DownloadsServiceParams) (DownloadsService, error) {
	if params.Cfg.Enable {
		repo := download.NewDownloadServerRepository(&params.Cfg)
		return newDownloadServerService(repo, params.Logger), nil
	}
	err := params.S3.Connect(context.Background())
	if err != nil {
		return nil, fmt.Errorf("error connecting to s3: %w", err)
	}
	return newDownloadService(params.Store, params.S3, params.Olap), nil
}

func newDownloadServerService(repo repositories.DownloadServerRepository, logger *logger.Logger) DownloadsService {
	return &DownloadServerService{
		repo:   repo,
		logger: logger,
	}
}

func (s *DownloadServerService) CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
	return s.repo.CreateAndStream(req)
}

func (s *DownloadServerService) List(userID, orgID string, limit, offset int32) ([]*models.Download, error) {
	return s.repo.List(userID, orgID, limit, offset)
}

func (s *DownloadServerService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.repo.Get(downloadID, userID, orgID)
}

func (s *DownloadServerService) Delete(downloadID, userID, orgID string) error {
	return s.repo.Delete(downloadID, userID, orgID)
}

type downloadService struct {
	store repositories.DownloadsRepository
	s3    repositories.S3SourceRepository
	olap  repositories.OlapRepository
}

func newDownloadService(store repositories.DownloadsRepository, s3 repositories.S3SourceRepository, olap repositories.OlapRepository) DownloadsService {
	return &downloadService{
		store: store,
		s3:    s3,
		olap:  olap,
	}
}

type SSEEvent struct {
	DownloadID string `json:"download_id"`
	Type       string `json:"type"`
	Message    string `json:"message"`
}

func (s *downloadService) CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
	ctx := context.Background()

	// This is a synchronous error before the stream starts.
	downloadJob, err := s.store.CreateDownload(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create download record: %w", err)
	}

	jobIDStr := downloadJob.ID.String()
	sseChan := make(chan models.DownloadsSSEData, 10)

	go func() {
		defer close(sseChan)

		// 1. Manually format and send the 'job_created' event first.
		jobCreatedPayload, _ := json.Marshal(downloadJob)
		jobCreatedMsg := fmt.Sprintf("event: job_created\ndata: %s\n\n", jobCreatedPayload)
		sseChan <- models.DownloadsSSEData{Data: []byte(jobCreatedMsg)}

		// Helper to format subsequent progress updates as 'data' only, like the reference.
		sendEvent := func(eventType, message string) {
			eventPayload := SSEEvent{
				DownloadID: jobIDStr,
				Type:       eventType,
				Message:    message,
			}
			payloadBytes, _ := json.Marshal(eventPayload)
			// Subsequent events are just 'data:', as per your reference handler's loop.
			sseMessage := fmt.Sprintf("data: %s\n\n", payloadBytes)
			sseChan <- models.DownloadsSSEData{Data: []byte(sseMessage)}
		}

		// Helper to format a terminal error.
		handleFailure := func(failErr error) {
			errMsg := failErr.Error()
			failReq := &models.SetDownloadFailedRequest{ErrorMessage: errMsg}
			s.store.SetDownloadAsFailed(ctx, jobIDStr, failReq)

			errorPayload, _ := json.Marshal(map[string]string{"type": "error", "message": errMsg})
			errorMsg := fmt.Sprintf("event: error\ndata: %s\n\n", errorPayload)
			sseChan <- models.DownloadsSSEData{Data: []byte(errorMsg)}
		}

		// 2. Proceed with the rest of the job, sending formatted status updates.
		if _, err := s.store.SetDownloadToProcessing(ctx, jobIDStr); err != nil {
			handleFailure(fmt.Errorf("failed to set job to processing: %w", err))
			return
		}
		sendEvent("status_update", "Processing query...")

		pr, pw := io.Pipe()
		s3Key := fmt.Sprintf("%s/%s.%s", downloadJob.OrgID, jobIDStr, downloadJob.Format)
		uploadErrChan := make(chan error, 1)

		go func() {
			defer close(uploadErrChan)
			_, uploadErr := s.s3.UploadFile(ctx, s3Key, pr)
			uploadErrChan <- uploadErr
		}()

		sendEvent("status_update", "Streaming data to storage...")
		dbErr := s.olap.ExecuteQueryAndStreamCSV(ctx, downloadJob.SQL, pw)
		pw.CloseWithError(dbErr)
		uploadErr := <-uploadErrChan

		if dbErr != nil || uploadErr != nil {
			finalErr := dbErr
			if finalErr == nil {
				finalErr = uploadErr
			}
			handleFailure(fmt.Errorf("data processing or upload failed: %w", finalErr))
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

func (s *downloadService) List(userID, orgID string, limit, offset int32) ([]*models.Download, error) {
	return s.store.ListDownloadsByUser(context.Background(), userID, orgID, limit, offset)
}

func (s *downloadService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.store.GetDownload(context.Background(), downloadID, orgID)
}

func (s *downloadService) Delete(downloadID, userID, orgID string) error {
	return s.store.DeleteDownload(context.Background(), downloadID, orgID)
}
