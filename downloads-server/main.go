package main

import "github.com/factly/gopie/downlods-server/cmd"

// @title Downloads Server API
// @version 1.0.0
// @description API for managing data export downloads with support for SQL queries and multiple formats
// @contact.name API Support
// @contact.email support@factly.org
// @license.name MIT
// @license.url https://opensource.org/licenses/MIT
// @host localhost:8000
// @BasePath /
// @schemes http https
// @securityDefinitions.apikey BearerAuth
// @in header
// @name Authorization
// @description JWT token for authentication
func main() {
	cmd.Execute()
}
