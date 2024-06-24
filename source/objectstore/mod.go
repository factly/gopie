package objectstore

import "context"

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
