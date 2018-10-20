"""Test the control module."""


def test_job_queue(center):
    """Test add a job and run a job."""
    store = []

    def calc_test(number1, number2):
        """Add number1 with number2."""
        return number1 + number2

    def get_result(result):
        """Store result."""
        store.append(result)

    center.add_job(calc_test, 1, 2, callback=get_result)

    assert not store

    center.run_job()

    assert len(store) == 1
    assert store[0] == 3


def test_run_job_without_job(center):
    """Test run a job without job."""
    store = []

    def calc_test(number1, number2):
        """Add number1 with number2."""
        return number1 + number2

    def get_result(result):
        """Store result."""
        store.append(result)

    center.add_job(calc_test, 1, 2, callback=get_result)

    assert not store
    center.run_job()
    assert len(store) == 1
    assert store[0] == 3
    center.run_job()
    assert len(store) == 1


def test_add_job_without_args(center):
    """Test add a job without args and run the job."""
    store = []

    def return_test():
        """Add number1 with number2."""
        return 10

    def get_result(result):
        """Store result."""
        store.append(result)

    center.add_job(return_test, callback=get_result)

    assert not store

    center.run_job()

    assert len(store) == 1
    assert store[0] == 10
