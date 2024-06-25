package objectstore

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage"
	"github.com/bmatcuk/doublestar/v4"
	"github.com/factly/gopie/pkg"
	"gocloud.dev/blob"
	"golang.org/x/sync/errgroup"
)

type FileIterator interface {
	Close() error
	Next() ([]string, error)
	Size(uint ProgressUnit) (int64, bool)
	Format() string
}

type ObjectStore interface {
	DownloadFiles(ctx context.Context, src map[string]any) (FileIterator, error)
}

type ProgressUnit int

const _concurrentBlobDownloadLimit = 8

var _ FileIterator = &blobIterator{}

func NewIterator(ctx context.Context, bucket *blob.Bucket, opts BlobOptions, logger pkg.Logger) (FileIterator, error) {
	opts.validate()
	tempDir, err := os.MkdirTemp(opts.TempDir, "blob_ingestion")
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithCancel(ctx)
	it := &blobIterator{
		opts:       &opts,
		logger:     logger,
		bucket:     bucket,
		tempDir:    tempDir,
		ctx:        ctx,
		cancel:     cancel,
		batchCh:    make(chan []string),
		downloadCh: make(chan downloadResult),
	}

	objects, err := it.getObjs()
	if err != nil {
		close(it.batchCh)
		it.Close()
		return nil, err
	}
	it.objects = objects

	go it.downloadFiles()

	go it.batchDownload()

	if len(objects) == 1 {
		it.opts.KeepFilesUntilClose = true
		batch, err := it.Next()
		if err != nil {
			it.Close()
			return nil, err
		}
		it.batchCh <- batch
		return &prefetchdIterator{batch: batch, underlying: it}, nil
	}

	return it, nil
}

var _partialDownloadReaders = map[string]string{
	".parquet": "parquet",
	".csv":     "csv",
}

type BlobOptions struct {
	GlobMaxTotalSize      int64
	GlobMaxObjectsMatched int
	GlobMaxObjectsListed  int64
	GlobPageSize          int
	GlobPattern           string
	StorageLimitInBytes   int64
	KeepFilesUntilClose   bool
	RetainFiles           bool
	BatchSizeBytes        int64
	Format                string
	TempDir               string
}

func (opts *BlobOptions) validate() {
	if opts.GlobMaxObjectsMatched == 0 {
		opts.GlobMaxObjectsMatched = 1000
	}
	if opts.GlobMaxObjectsListed == 0 {
		opts.GlobMaxObjectsListed = 10 * 1024 * 1024 * 1024
	}
	if opts.GlobPageSize == 0 {
		opts.GlobPageSize = 1000
	}
	if opts.BatchSizeBytes == 0 {
		opts.BatchSizeBytes = 2 * 1024 * 1024 * 1024
	}
}

func (opts *BlobOptions) validateLimits(size int64, matchCount int, fetched int64) error {
	if size > opts.GlobMaxTotalSize {
		return fmt.Errorf("glob pattern exceeds limits: would fetch more than %d bytes", opts.GlobMaxTotalSize)
	}
	if matchCount > opts.GlobMaxObjectsMatched {
		return fmt.Errorf("glob pattern exceeds limits: matched more than %d bytes", opts.GlobMaxTotalSize)
	}
	if fetched > opts.GlobMaxObjectsListed {
		return fmt.Errorf("glob pattern exceeds limits: listed more than %d bytes", opts.GlobMaxTotalSize)
	}
	return nil
}

type blobIterator struct {
	opts      *BlobOptions
	logger    pkg.Logger
	bucket    *blob.Bucket
	objects   []*blob.ListObject
	tempDir   string
	lastBatch []string

	ctx         context.Context
	cancel      func()
	batchCh     chan []string
	downloadCh  chan downloadResult
	downloadErr error
}

func (it *blobIterator) Close() error {
	it.cancel()
	var stop bool
	for !stop {
		_, ok := <-it.batchCh
		if !ok {
			stop = true
		}
	}

	var closeErr error

	if it.tempDir != "" && !it.opts.RetainFiles {
		err := os.RemoveAll(it.tempDir)
		if err != nil {
			closeErr = errors.Join(closeErr, err)
		}
	}

	err := it.bucket.Close()
	if err != nil {
		closeErr = errors.Join(closeErr, err)
	}
	return closeErr
}

func (it *blobIterator) Size(unit ProgressUnit) (int64, bool) {
	return int64(unit), true
}

func ForceRemoveFiles(paths []string) {
	for _, path := range paths {
		_ = os.Remove(path)
	}
}

func (it *blobIterator) Next() ([]string, error) {
	if !it.opts.KeepFilesUntilClose && !it.opts.RetainFiles {
		ForceRemoveFiles(it.lastBatch)
	}

	batch, ok := <-it.batchCh
	if !ok {
		if it.downloadErr != nil {
			return nil, it.downloadErr
		}
		return nil, io.EOF
	}

	it.lastBatch = batch

	result := make([]string, len(batch))
	copy(result, batch)
	return result, nil
}

func (it *blobIterator) downloadFiles() {
	defer close(it.downloadCh)

	g, ctx := errgroup.WithContext(it.ctx)
	g.SetLimit(_concurrentBlobDownloadLimit)

	var loopErr error
	for i := 0; i < len(it.objects); i++ {
		var stop bool
		select {
		case <-ctx.Done():
			stop = true
		default:
			// dont break
		}
		if stop {
			break
		}

		obj := it.objects[i]
		filename := filepath.Join(it.tempDir, obj.Key)
		if err := os.MkdirAll(filepath.Dir(filename), os.ModePerm); err != nil {
			loopErr = err
			it.cancel()
			break
		}

		g.Go(func() error {
			startTime := time.Now()
			var file *os.File
			err := retry(it.logger, 5, 10*time.Second, func() error {
				file, err := os.OpenFile(filename, os.O_RDWR|os.O_CREATE|os.O_TRUNC, os.ModePerm)
				if err != nil {
					return nil
				}
				defer file.Close()
				return downloadObj(ctx, it.bucket, obj.Key, file)
			})

			if err != nil {
				return err
			}
			it.downloadCh <- downloadResult{path: filename, bytes: obj.Size}

			duration := time.Since(startTime)
			_, err = file.Stat()

			it.logger.Info("dowload complete obj: %s, duration: %d", obj.Key, duration)
			return nil
		})
	}
	it.downloadErr = g.Wait()
	if loopErr != nil {
		it.downloadErr = loopErr
	}
}

type downloadResult struct {
	path  string
	bytes int64
}

func (it *blobIterator) Format() string {
	return it.opts.Format
}

func retry(logger pkg.Logger, maxRetries int, delay time.Duration, fn func() error) error {
	logger.Info("retrying to download...")
	var err error
	for i := 0; i < maxRetries; i++ {
		err = fn()
		if err == nil {
			return nil
		} else if strings.Contains(err.Error(), "stream error: stream ID") {
			time.Sleep(delay)
		} else {
			break
		}
	}
	return err
}

func downloadObj(ctx context.Context, bucket *blob.Bucket, objPath string, file *os.File) error {
	rc, err := bucket.NewReader(ctx, objPath, nil)
	if err != nil {
		return fmt.Errorf("Object(%q).NewReader: %w", objPath, err)
	}
	defer rc.Close()
	_, err = io.Copy(file, rc)
	return nil
}

func (it *blobIterator) batchDownload() {
	defer close(it.batchCh)

	var batch []string
	var batchBytes int64

	for {
		res, ok := <-it.downloadCh
		if !ok {
			if it.downloadErr == nil && len(batch) > 0 {
				it.batchCh <- batch
			}
			return
		}

		batch = append(batch, res.path)
		batchBytes += res.bytes
		if batchBytes >= it.opts.BatchSizeBytes {
			it.batchCh <- batch
			batch = nil
			batchBytes = 0
		}
	}
}

func (it *blobIterator) getObjs() ([]*blob.ListObject, error) {
	var (
		size, fetched int64
		matchCount    int
	)
	listOpts, ok := listOptions(it.opts.GlobPattern)
	if !ok {
		it.logger.Error("glob pattern corresponds to single object :%s", it.opts.GlobPattern)
		attr, err := it.bucket.Attributes(it.ctx, it.opts.GlobPattern)
		if err != nil {
			it.logger.Error("failed to fetch attributes of the object %w", err)
		} else {
			size = attr.Size
		}
		return []*blob.ListObject{{Key: it.opts.GlobPattern, Size: size}}, nil
	}

	token := blob.FirstPageToken
	var objects []*blob.ListObject
	for token != nil {
		objs, nextToken, err := it.bucket.ListPage(it.ctx, token, it.opts.GlobPageSize, listOpts)
		if err != nil {
			return nil, err
		}

		token = nextToken
		fetched += int64(len(objs))
		for _, obj := range objs {
			if matched, _ := doublestar.Match(it.opts.GlobPattern, obj.Key); matched {
				size += obj.Size
				matchCount++
				objects = append(objects, obj)
			}
		}
	}

	if err := it.opts.validateLimits(size, matchCount, fetched); err != nil {
		return nil, err
	}

	return objects, nil
}

func IsGlob(path string) bool {
	for i := 0; i < len(path); i++ {
		switch path[i] {
		case '*', '?', '[', '\\', '{':
			return true
		}
	}
	return false
}

func listOptions(globPattern string) (*blob.ListOptions, bool) {
	listOptions := &blob.ListOptions{BeforeList: func(as func(interface{}) bool) error {
		var q *storage.Query
		if as(&q) {
			_ = q.SetAttrSelection([]string{"Name", "Size"})
		}
		return nil
	}}
	prefix, glob := doublestar.SplitPattern(globPattern)
	if IsGlob(glob) {
		listOptions.Prefix = globPattern
		return nil, false
	} else if prefix != "." {
		listOptions.Prefix = prefix
	}

	return listOptions, true
}

type prefetchdIterator struct {
	batch      []string
	done       bool
	underlying *blobIterator
}

func (it *prefetchdIterator) Close() error {
	return it.underlying.Close()
}

func (it *prefetchdIterator) Size(unit ProgressUnit) (int64, bool) {
	return it.underlying.Size(unit)
}

func (it *prefetchdIterator) Next() ([]string, error) {
	if it.done {
		return nil, io.EOF
	}

	it.done = true
	return it.batch, nil
}

func (it *prefetchdIterator) Format() string {
	return it.underlying.Format()
}
