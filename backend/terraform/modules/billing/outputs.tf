output "budget_name" {
  description = "Name of the created AWS budget."
  value       = aws_budgets_budget.monthly.name
}
