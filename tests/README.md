# Tests

`tests/<module>/test_<topic>.py` mirrors `app/`. Name tests after the requirement, for example `test_fr_13_3_teaser_hides_file_name`, or after the task code when there is no FR.

- `e2e/`: Playwright scenarios run against staging
- `load/`: Locust load tests (`P4-PERF-01`)
