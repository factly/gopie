package duckdb

import (
	"fmt"

	pg_query "github.com/pganalyze/pg_query_go/v6"
	"vitess.io/vitess/go/vt/sqlparser"
)

// walkAndQualifyUnqualifiedTablesForPg recursively traverses a SELECT statement's AST
// and sets the provided schemaName for any table reference that is not already schema-qualified.
// Note: May not correctly distinguish between base tables and CTE references.
func walkAndQualifyUnqualifiedTablesForPg(node *pg_query.Node, schemaName string) {
	if node == nil {
		return
	}

	// Case 1: Direct table reference (RangeVar)
	if rv := node.GetRangeVar(); rv != nil {

		if rv.Schemaname == "" {

			fmt.Printf("SELECT context: Qualifying unqualified table '%s' with schema '%s'\n", rv.Relname, schemaName)
			rv.Schemaname = schemaName
		}

		return // Processed this RangeVar node.
	}

	// Case 2: Join expression
	if joinExpr := node.GetJoinExpr(); joinExpr != nil {
		walkAndQualifyUnqualifiedTablesForPg(joinExpr.Larg, schemaName)
		walkAndQualifyUnqualifiedTablesForPg(joinExpr.Rarg, schemaName)
		walkAndQualifyUnqualifiedTablesForPg(joinExpr.Quals, schemaName) // Join condition
		return
	}

	// Case 3: The SELECT statement itself
	if selStmtPayload := node.GetSelectStmt(); selStmtPayload != nil {
		// FROM clause
		if selStmtPayload.FromClause != nil {
			for _, fromItemNode := range selStmtPayload.FromClause {
				walkAndQualifyUnqualifiedTablesForPg(fromItemNode, schemaName)
			}
		}
		// WHERE clause
		if selStmtPayload.WhereClause != nil {
			walkAndQualifyUnqualifiedTablesForPg(selStmtPayload.WhereClause, schemaName)
		}
		// Target list (SELECTed expressions)
		if selStmtPayload.TargetList != nil {
			for _, targetItemNode := range selStmtPayload.TargetList {
				if resTarget := targetItemNode.GetResTarget(); resTarget != nil {
					// Recurse on the value of the result target, which can be an expression
					walkAndQualifyUnqualifiedTablesForPg(resTarget.Val, schemaName)
				}
			}
		}
		// WITH clause (Common Table Expressions)
		if withClause := selStmtPayload.GetWithClause(); withClause != nil {
			if withClause.Ctes != nil {
				for _, cteItemNode := range withClause.Ctes {
					if commonTableExpr := cteItemNode.GetCommonTableExpr(); commonTableExpr != nil {
						// The query defining the CTE must also be processed.
						if commonTableExpr.Ctequery != nil {
							walkAndQualifyUnqualifiedTablesForPg(commonTableExpr.Ctequery, schemaName)
						}
					}
				}
			}
		}
		// HAVING clause
		if selStmtPayload.HavingClause != nil {
			walkAndQualifyUnqualifiedTablesForPg(selStmtPayload.HavingClause, schemaName)
		}

		// For UNION, INTERSECT, EXCEPT (Set Operations)
		if selStmtPayload.Larg != nil {
			// Larg and Rarg are *pg_query.SelectStmt, so wrap them in a Node for recursion
			largNode := &pg_query.Node{Node: &pg_query.Node_SelectStmt{SelectStmt: selStmtPayload.Larg}}
			walkAndQualifyUnqualifiedTablesForPg(largNode, schemaName)
		}
		if selStmtPayload.Rarg != nil {
			rargNode := &pg_query.Node{Node: &pg_query.Node_SelectStmt{SelectStmt: selStmtPayload.Rarg}}
			walkAndQualifyUnqualifiedTablesForPg(rargNode, schemaName)
		}
		return
	}

	// Case 4: SubLink (subquery in an expression)
	if subLink := node.GetSubLink(); subLink != nil {
		walkAndQualifyUnqualifiedTablesForPg(subLink.Subselect, schemaName)
		if subLink.Testexpr != nil { // For subqueries used with ANY, ALL, EXISTS, etc.
			walkAndQualifyUnqualifiedTablesForPg(subLink.Testexpr, schemaName)
		}
		return
	}

	// Case 5: General expressions (A_Expr for arithmetic/comparison, BoolExpr for AND/OR/NOT)
	if aExpr := node.GetAExpr(); aExpr != nil {
		walkAndQualifyUnqualifiedTablesForPg(aExpr.Lexpr, schemaName)
		walkAndQualifyUnqualifiedTablesForPg(aExpr.Rexpr, schemaName)
		return
	}
	if boolExpr := node.GetBoolExpr(); boolExpr != nil {
		if boolExpr.Args != nil {
			for _, argItemNode := range boolExpr.Args {
				walkAndQualifyUnqualifiedTablesForPg(argItemNode, schemaName)
			}
		}
		return
	}
	// Function calls
	if funcCall := node.GetFuncCall(); funcCall != nil {
		// Arguments to the function
		if funcCall.Args != nil {
			for _, argItemNode := range funcCall.Args {
				walkAndQualifyUnqualifiedTablesForPg(argItemNode, schemaName)
			}
		}
		// Window definition (OVER clause)
		if funcCall.Over != nil { // funcCall.Over is *pg_query.WindowDef
			if funcCall.Over.PartitionClause != nil {
				for _, partItemNode := range funcCall.Over.PartitionClause {
					walkAndQualifyUnqualifiedTablesForPg(partItemNode, schemaName)
				}
			}
			if funcCall.Over.OrderClause != nil {
				for _, orderItemNode := range funcCall.Over.OrderClause { // Each is a Node, typically SortBy
					if sortBy := orderItemNode.GetSortBy(); sortBy != nil {
						walkAndQualifyUnqualifiedTablesForPg(sortBy.Node, schemaName)
					} else {
						// Fallback if it's not a SortBy node but some other expression
						walkAndQualifyUnqualifiedTablesForPg(orderItemNode, schemaName)
					}
				}
			}
			if funcCall.Over.StartOffset != nil {
				walkAndQualifyUnqualifiedTablesForPg(funcCall.Over.StartOffset, schemaName)
			}
			if funcCall.Over.EndOffset != nil {
				walkAndQualifyUnqualifiedTablesForPg(funcCall.Over.EndOffset, schemaName)
			}
		}
		return
	}

	// Case 6: A WindowDef node itself (e.g., from a WINDOW clause)
	if windowDef := node.GetWindowDef(); windowDef != nil {
		if windowDef.PartitionClause != nil {
			for _, partItemNode := range windowDef.PartitionClause {
				walkAndQualifyUnqualifiedTablesForPg(partItemNode, schemaName)
			}
		}
		if windowDef.OrderClause != nil {
			for _, orderItemNode := range windowDef.OrderClause { // Each is a Node, typically SortBy
				if sortBy := orderItemNode.GetSortBy(); sortBy != nil {
					walkAndQualifyUnqualifiedTablesForPg(sortBy.Node, schemaName)
				} else {
					walkAndQualifyUnqualifiedTablesForPg(orderItemNode, schemaName)
				}
			}
		}
		if windowDef.StartOffset != nil {
			walkAndQualifyUnqualifiedTablesForPg(windowDef.StartOffset, schemaName)
		}
		if windowDef.EndOffset != nil {
			walkAndQualifyUnqualifiedTablesForPg(windowDef.EndOffset, schemaName)
		}
		return
	}

	// Case 7: A list of nodes (generic list, e.g., arguments to some operators)
	if listNode := node.GetList(); listNode != nil {
		for _, itemNode := range listNode.Items {
			walkAndQualifyUnqualifiedTablesForPg(itemNode, schemaName)
		}
		return
	}

	// Case 8: ResTarget (an item in the SELECT list, e.g., "column_name AS alias" or "expr AS alias")
	if resTarget := node.GetResTarget(); resTarget != nil {
		// resTarget.Name is the alias (optional).
		// resTarget.Val is the expression being selected. Recurse into the expression.
		walkAndQualifyUnqualifiedTablesForPg(resTarget.Val, schemaName)
		return
	}
}

// mysqlQualifierWalker holds the schema name and defined CTEs for the current walk.
type mysqlQualifierWalker struct {
	schemaName string
	cteNames   map[string]bool
}

// newMySQLQualifierWalker creates a new walker.

func newMySQLQualifierWalker(schemaName string, currentCteNames map[string]bool) *mysqlQualifierWalker {
	return &mysqlQualifierWalker{
		schemaName: schemaName,
		cteNames:   currentCteNames,
	}
}

func (w *mysqlQualifierWalker) visitorFunc(node sqlparser.SQLNode) (kontinue bool, err error) {
	switch n := node.(type) {
	case *sqlparser.AliasedTableExpr:
		if tnValue, ok := n.Expr.(sqlparser.TableName); ok {
			if w.cteNames != nil {
				if _, isCTE := w.cteNames[tnValue.Name.String()]; isCTE {
					return true, nil
				}
			}

			if tnValue.Qualifier.IsEmpty() {

				tnValue.Qualifier = sqlparser.NewIdentifierCS(w.schemaName)

				n.Expr = tnValue
			}
		}
	}
	return true, nil
}

// getWithClause is a helper to extract the *sqlparser.With clause from common statement types.
func getWithClause(stmt sqlparser.SQLNode) *sqlparser.With {
	switch s := stmt.(type) {
	case *sqlparser.Select:
		return s.With
	}
	return nil
}

// WalkAndQualifyUnqualifiedTablesForMySQL traverses a MySQL statement's AST
// and applies the schemaName for unqualified table references, ignoring CTE references.
func WalkAndQualifyUnqualifiedTablesForMySQL(stmtNode sqlparser.SQLNode, schemaName string) error {
	if stmtNode == nil {
		return nil
	}

	// Pre-collect CTE names from the top-level of the given stmtNode.
	// This helps distinguish CTE references from base tables within the main query body.
	// Tables *inside* CTE definitions will be qualified by the recursive walk if they are base tables.
	currentCteNames := make(map[string]bool)
	if wClause := getWithClause(stmtNode); wClause != nil {
		for _, cte := range wClause.CTEs {
			currentCteNames[cte.ID.String()] = true
		}
	}

	walker := newMySQLQualifierWalker(schemaName, currentCteNames)

	// sqlparser.Walk takes one visitor function and the node(s) to walk.
	// Modifications to the AST are made in-place.
	err := sqlparser.Walk(walker.visitorFunc, stmtNode)
	if err != nil {
		return fmt.Errorf("error walking MySQL AST for table qualification: %w", err)
	}

	return nil
}
