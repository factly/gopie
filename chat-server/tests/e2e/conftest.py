def pytest_addoption(parser):
    parser.addoption(
        "--disable-formatter",
        action="store_true",
        default=False,
        help="Disable terminal formatter output for cleaner pytest output"
    )
