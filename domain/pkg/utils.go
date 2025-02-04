package pkg

import (
	"math/rand"
	"strconv"
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
		return 10, 1
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
