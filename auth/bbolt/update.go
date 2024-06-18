package bbolt

import (
	"github.com/factly/gopie/auth/models"
	"go.etcd.io/bbolt"
)

func (b *Bbolt) UpdateKey(k models.AuthToken, m map[string]any) (*models.AuthKey, error) {
	key, err := b.GetKey(k)
	if err != nil {
		return nil, err
	}

	key = key.UpdateFromMap(m)

	err = b.Batch(func(tx *bbolt.Tx) error {
		b := tx.Bucket(bucketName)

		k := key.Token.ToBytes()

		v, err := key.StructToBytes()
		if err != nil {
			return err
		}

		err = b.Put(k, v)
		if err != nil {
			return err
		}

		return nil
	})

	return nil, nil
}
