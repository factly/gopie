package pkg

import (
	"fmt"
	"math/rand"
	"strconv"

	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/go-playground/validator/v10"
)

func ParseLimitAndPage(limitStr, pageStr string) (int, int) {
	limit := 10
	page := 1
	var err error

	if limitStr != "" {
		limit, err = strconv.Atoi(limitStr)
		if err != nil {
			return 10, 1
		}
	}

	if pageStr != "" {
		page, err = strconv.Atoi(pageStr)
		if err != nil {
			return 10, 1
		}
	}

	return limit, page
}

const charset = "abcdefghijklmnopqrstuvwxyz" +
	"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

func RandomString(length uint) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[rand.Intn(len(charset))]
	}
	return string(b)
}

// parseAndValidateRequest parses and validates the upload request
func ValidateRequest(logger *logger.Logger, req any) error {
	if err := validator.New().Struct(req); err != nil {
		fmt.Println(err)
		return fmt.Errorf("Invalid request body: %v", err)
	}

	return nil
}
