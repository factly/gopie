package pkg

import (
	"fmt"
	"strings"
)

type URL struct {
	Scheme string
	Host   string
	Path   string
}

// ParseBucketURL splits urls iwth globs into scheme, hostname and rest of the url(as glob).
// url.Parse removes `?` considering it as query param.
// `?` is valid meta in glob pattern.
func ParseBucketURL(path string) (*URL, error) {
	scheme, path, ok := strings.Cut(path, "://")
	if !ok {
		return nil, fmt.Errorf("failed to parse URL '%q'", path)
	}

	host, path, ok := strings.Cut(path, "/")
	if !ok {
		// This is actually valid URL, just not a valid object storage URL.
		return nil, fmt.Errorf("failed to parsel URL '%q'", path)
	}

	return &URL{Scheme: scheme, Host: host, Path: path}, nil
}
