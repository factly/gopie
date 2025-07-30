package duckdbsql

import (
	"errors"
	"strconv"
)

func (a *AST) traverse() error {
	if toBoolean(a.ast, astKeyError) {
		originalErr := errors.New(toString(a.ast, astKeyErrorMessage))
		pos := toString(a.ast, astKeyPosition)
		if pos == "" {
			return originalErr
		}

		num, err := strconv.Atoi(pos)
		if err != nil {
			return err
		}

		return PositionError{
			originalErr,
			num,
		}
	}

	statements := toNodeArray(a.ast, astKeyStatements)
	if len(statements) == 0 {
		return errors.New("no statement found")
	}

	for _, statement := range statements {
		a.traverseSelectQueryStatement(toNode(statement, astKeyNode), true)
	}

	return nil
}

func (a *AST) traverseSelectQueryStatement(node astNode, isRoot bool) {
	if node == nil {
		return
	}

	if isRoot {
		sn := &selectNode{
			ast: node,
		}
		a.rootNodes = append(a.rootNodes, sn)
	}

	switch toString(node, astKeyType) {
	case "SELECT_NODE":
		// We only need the root node, but we check for CTEs to traverse deeper if needed.
		a.traverseSelectQueryStatement(toNode(toNode(node, astKeyCTE), "query"), false)
	case "SET_OPERATION_NODE":
		// For UNION, INTERSECT, etc., traverse both sides. The root is the SET_OPERATION_NODE itself.
		a.traverseSelectQueryStatement(toNode(node, astKeyLeft), false)
		a.traverseSelectQueryStatement(toNode(node, astKeyRight), false)
	}
}

type PositionError struct {
	error
	Position int
}

func (e PositionError) Err() error {
	return e.error
}
