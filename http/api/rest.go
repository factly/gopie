package api

import (
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"

	"github.com/factly/gopie/http/middleware"
	"github.com/factly/x/renderx"
	"github.com/go-chi/chi/v5"
)

func (h *httpHandler) rest(w http.ResponseWriter, r *http.Request) {
	// get the table name from path param
	table := chi.URLParam(r, "tableName")
	queryParams := r.URL.Query()

	query, err := buildQuery(table, queryParams)
	if err != nil {
		h.handleError(w, err, "error building query", http.StatusBadRequest)
		return
	}

	query = imposeLimits(query)

	res, err := h.executeQuery(query, table)

	if err != nil {
		h.handleError(w, err, "Error executing query", http.StatusInternalServerError)
		return
	}

	jsonRes, err := res.RowsToMap()
	if err != nil {
		h.handleError(w, err, "Error converting result to JSON", http.StatusInternalServerError)
	}

	subject, ok := middleware.GetSubjectFromContext(r.Context())
	if ok {
		params := ingestEventParams{
			subject:        subject,
			dataset:        table,
			userID:         r.Header.Get("x-gopie-user-id"),
			organisationID: r.Header.Get("x-gopie-organisation-id"),
			method:         r.Method,
			endpoint:       r.URL.String(),
		}
		ingestEvent(h.metering, params)
	} else {
		h.logger.Error("Failed to retrieve subject")
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

func buildQuery(table string, queryParams url.Values) (string, error) {
	// get the columns of the table
	columns := queryParams.Get("columns")
	if columns == "" {
		columns = "*"
	}

	// initialize base query
	query := fmt.Sprintf("SELECT %s FROM %s", columns, table)

	// valid filter is of pattern filter[column_name](gt|lt)=value
	// value if a string should only wrapped around with single quotes
	// value if not wrapped with single quotes are considered numbers and are parsed
	// that means filter[col]lt='value', filter[col]=5 are valid filters
	// where as filter[col]gt="value", filter[col]=value and filter[col]=Phase5 are invalid filters
	whereQuery, err := parseFilters(queryParams)
	if err != nil {
		return "", err
	}

	if whereQuery != "" {
		query = fmt.Sprintf("%s %s", query, whereQuery)
	}

	sort := queryParams.Get("sort")
	if sort != "" {
		orderBy := parseSort(sort)
		query = fmt.Sprintf("%s %s", query, orderBy)
	}

	l := 0
	limit := queryParams.Get("limit")
	if limit != "" {
		parsedLimit, err := strconv.Atoi(limit)
		if err != nil {
			return "", err
		}
		if parsedLimit > 1000 {
			parsedLimit = 1000
		}
		l = parsedLimit
		query = fmt.Sprintf("%s LIMIT %d", query, parsedLimit)
	}

	page := queryParams.Get("page")
	if page != "" {
		parsedPage, err := strconv.Atoi(page)
		if err != nil {
			return "", err
		}
		query = fmt.Sprintf("%s OFFSET %d", query, (parsedPage-1)*l)
	}

	return imposeLimits(query), nil
}

func parseSort(sort string) string {
	split := strings.Split(sort, ",")
	query := "ORDER BY"
	if strings.HasPrefix(split[0], "-") {
		s := strings.TrimPrefix(split[0], "-")
		query = fmt.Sprintf("%s %s DESC", query, s)
	} else {
		query = fmt.Sprintf("%s %s ASC", query, split[0])
	}

	for _, s := range split[1:] {
		if strings.HasPrefix(s, "-") {
			s := strings.TrimPrefix(s, "-")
			query = fmt.Sprintf("%s, %s DESC", query, s)
		} else {
			query = fmt.Sprintf("%s, %s ASC", query, s)
		}
	}
	return query
}

func parseFilters(queryParams url.Values) (string, error) {
	filters := make(map[string]string)
	for key, values := range queryParams {
		if len(values) > 0 && len(key) >= len("filter") && key[:len("filter")] == "filter" {
			filters[key] = values[0]
		}
	}

	whereConditions := []string{}

	for key, value := range filters {
		err := validateFilterValues(value)
		if err != nil {
			return "", err
		}
		procesedKey, err := validateAndProcessFilterKey(key)
		if err != nil {
			return "", err
		}

		condition := fmt.Sprintf("%s= %s", procesedKey, value)

		whereConditions = append(whereConditions, condition)
	}
	if len(whereConditions) == 0 {
		return "", nil
	}
	return "WHERE " + strings.Join(whereConditions, " AND "), nil
}

func validateFilterValues(value string) error {
	if strings.HasPrefix(value, "'") {
		if !strings.HasSuffix(value, "'") {
			return fmt.Errorf("invalid filter value %s", value)
		}
		return nil
	} else if strings.HasSuffix(value, `"`) {
		return fmt.Errorf(`invalid filter value %s, value cannot start with " `, value)
	} else {
		if _, err := strconv.Atoi(value); err != nil {
			if _, err := strconv.ParseFloat(value, 64); err != nil {
				return fmt.Errorf("value should be a string starting and ending with ' or a number")
			}
		}
	}
	return nil
}

func validateAndProcessFilterKey(key string) (string, error) {
	// Define a regular expression pattern for the filter key
	pattern := `^filter\[([^\]]+)\](lt|gt)?$`
	r := regexp.MustCompile(pattern)
	match := r.FindStringSubmatch(key)
	if match == nil {
		return "", fmt.Errorf("filter does not follow the format filter[key](lt|gt|nothing)")
	}
	filterKey := match[1]
	ltgt := match[2]
	// Wrap filterKey in double quotes
	filterKey = fmt.Sprintf("\"%s\"", filterKey)

	// If lt or gt exists, append it to the filter key
	if ltgt != "" {
		if ltgt == "lt" {
			filterKey = fmt.Sprintf("%s <", filterKey)
		} else {

			filterKey = fmt.Sprintf("%s >", filterKey)
		}
	}
	return filterKey, nil
}
