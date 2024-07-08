package models

import (
	"encoding/json"
	"time"

	"github.com/mitchellh/mapstructure"
)

type AuthToken string

func (a AuthToken) ToBytes() []byte {
	return []byte(a)
}

type AuthKey struct {
	Description string         `json:"description,omitempty" mapstructure:"description"`
	Name        string         `json:"name" mapstructure:"name"`
	Token       AuthToken      `json:"token" mapstructure:"token"`
	Meta        map[string]any `json:"meta" mapstructure:"meta"`
	ExpiresAt   int64          `json:"expires_at" mapstructure:"expires_at"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
}

func (a *AuthKey) CreateFromMap(m map[string]any) {
	mapstructure.WeakDecode(m, a)

	// assign values
	a.CreatedAt = time.Now()
	a.UpdatedAt = time.Now()

	// set key expiry
	a.ExpiresAt = m["expires_at"].(int64)

}

func (a *AuthKey) UpdateFromMap(m map[string]any) *AuthKey {
	// if a nil update body is passed just invalidate the key
	if m == nil {
		a.Invalidate()
		return a
	}
	mapstructure.WeakDecode(m, a)
	return a
}

func (a *AuthKey) StructToBytes() ([]byte, error) {
	tempStruct := struct {
		Description string         `json:"description,omitempty"`
		Name        string         `json:"name"`
		ExpiresAt   int64          `json:"expires_at"`
		CreatedAt   time.Time      `json:"created_at"`
		UpdatedAt   time.Time      `json:"updated_at"`
		Meta        map[string]any `json:"meta,omitempty"`
	}{
		Description: a.Description,
		Name:        a.Name,
		ExpiresAt:   a.ExpiresAt,
		CreatedAt:   a.CreatedAt,
		Meta:        a.Meta,
		UpdatedAt:   a.UpdatedAt,
	}
	return json.Marshal(tempStruct)
}

func (a *AuthKey) Invalidate() {
	a.ExpiresAt = 0
}
