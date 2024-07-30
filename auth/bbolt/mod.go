package bbolt

import (
	"github.com/factly/gopie/pkg"
	"go.etcd.io/bbolt"
)

var (
	bucketName = []byte("gopie")
)

// bbolt is a embedded database
// This instance performs all the db crud operations for AuthKey Model
type Bbolt struct {
	path string
}

func (c *Bbolt) openConn() (*bbolt.DB, error) {
	return bbolt.Open(c.path, 0600, nil)
}

// Create a new BboltAuth Instance
func NewBboltInstance(path string, logger *pkg.Logger) (*Bbolt, error) {
	// open bbolt db from the given path
	db, err := bbolt.Open(path, 0600, nil)
	if err != nil {
		return nil, err
	}

	defer db.Close()
	// create new bucket called gopie
	db.Update(func(tx *bbolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists([]byte(bucketName))
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	})

	return &Bbolt{path}, nil
}

func matchObj(obj map[string]interface{}, match map[string]string) bool {
	for k, v := range match {
		if objV, ok := obj[k]; !ok || objV != v {
			return false
		}
	}
	return true
}
