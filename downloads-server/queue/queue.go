package queue

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/factly/gopie/downlods-server/duckdb"
	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/postgres"
	"github.com/factly/gopie/downlods-server/s3"
	"go.uber.org/zap"
)

type DownloadQueue struct {
	DbStore       *postgres.PostgresStore
	olapStore     *duckdb.OlapDBDriver
	logger        *logger.Logger
	s3ObjectStore *s3.S3ObjectStore
	Manager       *SubscriptionManager
	jobChannel    chan *models.Download
	numWorkers    int
}

func NewDownloadQueue(db *postgres.PostgresStore, olapStore *duckdb.OlapDBDriver, s3 *s3.S3ObjectStore, log *logger.Logger, manager *SubscriptionManager, cfg *config.QueueConfig) *DownloadQueue {
	return &DownloadQueue{
		DbStore:       db,
		olapStore:     olapStore,
		s3ObjectStore: s3,
		logger:        log,
		Manager:       manager,
		jobChannel:    make(chan *models.Download, cfg.QueueSize),
		numWorkers:    cfg.NumWorkers,
	}
}

func (q *DownloadQueue) Start() {
	q.logger.Info("Starting download queue worker")
	for i := range q.numWorkers {
		go q.worker(i)
	}
}

func (q *DownloadQueue) Submit(ctx context.Context, req *models.CreateDownloadRequest) (*models.Download, error) {
	q.logger.Info("Submitting new download request", zap.String("dataset_id", req.DatasetID))

	downloadJob, err := q.DbStore.CreateDownload(ctx, req)
	if err != nil {
		q.logger.Error("Failed to create download record in database", zap.Error(err))
		return nil, err
	}

	q.jobChannel <- downloadJob
	q.logger.Info("Successfully submitted download job", zap.String("download_id", downloadJob.ID.String()))

	return downloadJob, nil
}

func (q *DownloadQueue) worker(id int) {
	q.logger.Info("Worker started", zap.Int("worker_id", id))
	for job := range q.jobChannel {
		q.logger.Info("Worker processing download job",
			zap.Int("worker_id", id),
			zap.String("download_id", job.ID.String()),
		)
		q.processJob(job)
	}
}

func (q *DownloadQueue) processJob(job *models.Download) {
	ctx := context.Background()
	jobIDStr := job.ID.String()

	_, err := q.DbStore.SetDownloadToProcessing(ctx, jobIDStr)
	if err != nil {
		q.logger.Error("Failed to set job to processing", zap.String("download_id", jobIDStr), zap.Error(err))
		return
	}
	q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "status_update", Message: "Processing query..."})

	pr, pw := io.Pipe()
	s3Key := fmt.Sprintf("%s/%s.csv", job.OrgID, job.ID)

	errChan := make(chan error, 1)

	go func() {
		defer close(errChan)
		defer pr.Close()

		_, uploadErr := q.s3ObjectStore.UploadFile(ctx, s3Key, pr)
		if uploadErr != nil {
			pw.CloseWithError(uploadErr)
		}
		errChan <- uploadErr
	}()

	q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "status_update", Message: "Streaming data to storage..."})
	dbErr := q.olapStore.ExecuteQueryAndStreamCSV(ctx, job.SQL, pw)

	pw.Close()

	uploadErr := <-errChan

	if uploadErr != nil || dbErr != nil {
		finalErr := uploadErr
		if finalErr == nil {
			finalErr = dbErr
		}

		q.logger.Error("Failed to process and upload data", zap.String("download_id", jobIDStr), zap.Error(finalErr))
		failReq := &models.SetDownloadFailedRequest{ErrorMessage: finalErr.Error()}
		q.DbStore.SetDownloadAsFailed(ctx, jobIDStr, failReq)
		q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "error", Message: "Failed during data processing: " + finalErr.Error()})
		return
	}

	q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "status_update", Message: "Generating secure download link..."})
	expiresIn := 24 * time.Hour
	url, err := q.s3ObjectStore.GetPresignedURL(ctx, s3Key, expiresIn)
	if err != nil {
		failReq := &models.SetDownloadFailedRequest{ErrorMessage: "Failed to generate download link."}
		q.DbStore.SetDownloadAsFailed(ctx, jobIDStr, failReq)
		q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "error", Message: "Failed to generate download link."})
		return
	}

	completeReq := &models.SetDownloadCompletedRequest{PreSignedURL: url, ExpiresAt: time.Now().Add(expiresIn)}
	_, err = q.DbStore.SetDownloadAsCompleted(ctx, jobIDStr, completeReq)
	if err != nil {
		q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "error", Message: "Failed to finalize job status."})
		return
	}

	q.Manager.Broadcast(ProgressEvent{DownloadID: jobIDStr, Type: "complete", Message: url})
	q.logger.Info("Successfully processed download job", zap.String("download_id", jobIDStr))
}
