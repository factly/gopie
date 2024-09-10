package auth

import (
	"context"
	"fmt"

	meterus "github.com/elliot14A/meterus-go"
	"google.golang.org/protobuf/types/known/structpb"
)

type IAPIKey interface {
	ValidateKey(k string) (string, error)
}

type MeterusAPIKey struct {
	client *meterus.MeterusClient
}

func NewAuth(client *meterus.MeterusClient) (IAPIKey, error) {
	return &MeterusAPIKey{client}, nil
}

func (a *MeterusAPIKey) ValidateKey(k string) (string, error) {
	res, err := a.client.ValidateApiKey(context.Background(), k, []string{"meterus:gopie"})
	if err != nil {
		fmt.Println(err)
		return "", err
	}

	subject, err := extractSubject(res.Metadata)
	if err != nil {
		return "", err
	}

	return subject, nil
}

func extractSubject(metadata *structpb.Struct) (string, error) {
	if metadata == nil {
		return "", fmt.Errorf("metadata is nil")
	}

	subjectValue, ok := metadata.Fields["subject"]
	if !ok {
		return "", fmt.Errorf("subject field not found in metadata")
	}

	subject, ok := subjectValue.Kind.(*structpb.Value_StringValue)
	if !ok {
		return "", fmt.Errorf("subject is not a string value")
	}

	return subject.StringValue, nil
}
