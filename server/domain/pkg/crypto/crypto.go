package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"io"
)

// EncryptString encrypts a string using AES-GCM
func EncryptString(plaintext string, key []byte) (string, error) {
	if len(key) != 32 {
		return "", errors.New("key length must be 32 bytes (256 bits)")
	}

	// Create a new cipher block from the key
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	// Create a new GCM with the block
	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	// Create a nonce
	nonce := make([]byte, aesGCM.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}

	// Encrypt the plaintext
	ciphertext := aesGCM.Seal(nonce, nonce, []byte(plaintext), nil)

	// Return base64 encoded string
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// DecryptString decrypts a string using AES-GCM
func DecryptString(ciphertext string, key []byte) (string, error) {
	if len(key) != 32 {
		return "", errors.New("key length must be 32 bytes (256 bits)")
	}

	// Decode the base64 ciphertext
	data, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return "", err
	}

	// Create a new cipher block from the key
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	// Create a new GCM with the block
	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	// Get the nonce size
	nonceSize := aesGCM.NonceSize()
	if len(data) < nonceSize {
		return "", errors.New("ciphertext too short")
	}

	// Extract the nonce and ciphertext
	nonce, ciphertextBytes := data[:nonceSize], data[nonceSize:]

	// Decrypt the ciphertext
	plaintext, err := aesGCM.Open(nil, nonce, ciphertextBytes, nil)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}
