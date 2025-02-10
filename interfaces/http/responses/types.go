package responses

// ErrorResponse represents an error response
// @Description Error response structure
type ErrorResponse struct {
	// Error code
	Code int `json:"code" example:"400"`
	// Error message
	Message string `json:"message" example:"Invalid request parameters"`
	// Error details
	Error string `json:"error" example:"Validation failed"`
}

// SuccessResponse represents a success response with data
// @Description Success response structure with data
type SuccessResponse struct {
	// Response data
	Data interface{} `json:"data"`
}
