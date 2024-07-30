package bbolt

import (
	"github.com/factly/gopie/auth/models"
	"go.etcd.io/bbolt"
)

func (b *Bbolt) CreateKey(m map[string]any) (*models.AuthKey, error) {
	key := &models.AuthKey{}
	key.CreateFromMap(m)

	db, err := b.openConn()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	err = db.Batch(func(tx *bbolt.Tx) error {
		b := tx.Bucket(bucketName)

		v, err := key.StructToBytes()
		if err != nil {
			return err
		}

		err = b.Put(key.Token.ToBytes(), v)
		if err != nil {
			return err
		}
		return nil
	})

	return key, err
}
