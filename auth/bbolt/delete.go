package bbolt

import (
	"encoding/json"

	"github.com/factly/gopie/auth/models"
	"go.etcd.io/bbolt"
)

func (b *Bbolt) DeleteKey(k models.AuthToken) error {

	err := b.Batch(func(tx *bbolt.Tx) error {
		b := tx.Bucket(bucketName)
		err := b.Delete(k.ToBytes())
		return err
	})

	return err
}

func (b *Bbolt) DeleteAllKeys(match map[string]string) error {
	err := b.Batch(func(tx *bbolt.Tx) error {

		b := tx.Bucket(bucketName)

		err := b.ForEach(func(k, v []byte) error {
			var obj map[string]any
			if err := json.Unmarshal(v, &obj); err != nil {
				return err
			}

			if obj["meta"] == nil {
				return nil
			}
			if matchObj(obj["meta"].(map[string]string), match) {
				b.Delete(k)
			}
			return nil
		})

		return err
	})

	return err
}
