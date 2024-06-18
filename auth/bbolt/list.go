package bbolt

import (
	"encoding/json"

	"github.com/factly/gopie/auth/models"
	"go.etcd.io/bbolt"
)

func (b *Bbolt) ListKeys(match map[string]string) ([]*models.AuthKey, error) {
	var results []*models.AuthKey

	err := b.View(func(tx *bbolt.Tx) error {
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
				authKey := models.AuthKey{}
				authKey.CreateFromMap(obj)
				results = append(results, &authKey)
			}

			return nil
		})
		return err
	})

	return results, err
}
