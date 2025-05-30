package models

// DatasetSummary represents statistical summary information for a dataset column
// @Description Dataset summary statistics for columns
type DatasetSummary struct {
	// Name of the column
	ColumnName string `json:"column_name" example:"sales_amount"`
	// Data type of the column
	ColumnType string `json:"column_type" example:"numeric"`
	// Minimum value in the column
	Min string `json:"min" example:"10.5"`
	// Maximum value in the column
	Max string `json:"max" example:"1000.75"`
	// Approximate number of unique values
	ApproxUnique int64 `json:"approx_unique" example:"120"`
	// Average value of the column
	Avg string `json:"avg" example:"456.25"`
	// Standard deviation of the column values
	Std string `json:"std" example:"152.3"`
	// 25th percentile value
	Q25 string `json:"q25" example:"245.5"`
	// 50th percentile value (median)
	Q50 string `json:"q50" example:"450.8"`
	// 75th percentile value
	Q75 string `json:"q75" example:"675.2"`
	// Count of values
	Count int64 `json:"count" example:"1000"`
	// Percentage of null values
	NullPercentage any `json:"null_percentage" example:"2.5"`
	// Description of the column
	Description string `json:"description,omitempty" example:"Total sales amount for each transaction"`
}

type DatasetSummaryWithName struct {
	DatasetName string            `json:"dataset_name" example:"sales_data"`
	Summary     *[]DatasetSummary `json:"summary"`
}
