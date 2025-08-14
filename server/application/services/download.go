package services

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
)

type DownloadServerService struct {
	repo   repositories.DownloadServerRepository
	logger *logger.Logger
}

func NewDownloadServerService(repo repositories.DownloadServerRepository, logger *logger.Logger) *DownloadServerService {
	return &DownloadServerService{
		repo:   repo,
		logger: logger,
	}
}

func (s *DownloadServerService) CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
	return s.repo.CreateAndStream(req)
}

func (s *DownloadServerService) List(userID, orgID string, limit, offset int) ([]models.Download, error) {
	return s.repo.List(userID, orgID, limit, offset)
}

func (s *DownloadServerService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.repo.Get(downloadID, userID, orgID)
}

func (s *DownloadServerService) Delete(downloadID, userID, orgID string) error {
	return s.repo.Delete(downloadID, userID, orgID)
}

type DowloadService struct {
	store repositories.DownloadsRepository
	s3    repositories.S3SourceRepository
	olap  repositories.OlapRepository
}

func NewDownloadService(store repositories.DownloadsRepository, s3 repositories.S3SourceRepository, olap repositories.OlapRepository) *DowloadService {
	return &DowloadService{
		store: store,
		s3:    s3,
		olap:  olap,
	}
}

type SSEEvent struct {
	DownloadID string `json:"download_id"`
	Type       string `json:"type"`    // e.g., "status_update", "complete"
	Message    string `json:"message"` // e.g., "Processing query...", "https://s3..."
}

func (s *DowloadService) CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
	ctx := context.Background()

	downloadJob, err := s.store.CreateDownload(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create download record: %w", err)
	}

	jobIDStr := downloadJob.ID.String()
	sseChan := make(chan models.DownloadsSSEData, 10) // Buffered channel

	go func() {
		defer close(sseChan)

		sendEvent := func(eventType, message string) {
			event := SSEEvent{
				DownloadID: jobIDStr,
				Type:       eventType,
				Message:    message,
			}
			eventJSON, _ := json.Marshal(event)
			sseChan <- models.DownloadsSSEData{Data: eventJSON}
		}

		handleFailure := func(failErr error) {
			errMsg := failErr.Error()
			failReq := &models.SetDownloadFailedRequest{ErrorMessage: errMsg}
			s.store.SetDownloadAsFailed(ctx, jobIDStr, failReq)
			sseChan <- models.DownloadsSSEData{Error: failErr}
		}

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
