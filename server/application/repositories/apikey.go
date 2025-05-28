package repositories

type ApiKeyRepository interface {
	Validate(key string) (bool, error)
}
