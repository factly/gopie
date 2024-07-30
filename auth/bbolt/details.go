package bbolt

import (
	"encoding/json"

	"github.com/factly/gopie/auth/models"
	"go.etcd.io/bbolt"
)

func (b *Bbolt) GetKey(k models.AuthToken) (*models.AuthKey, error) {

	var key models.AuthKey

	db, err := b.openConn()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	err = db.View(func(tx *bbolt.Tx) error {
		b := tx.Bucket(bucketName)
		v := b.Get(k.ToBytes())
		err := json.Unmarshal(v, &key)
		if err != nil {
			return err
		}
		return nil
	})

	key.Token = k

	return &key, err
}
