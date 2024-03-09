from locust import FastHttpUser, task


class TestUser(FastHttpUser):
    """
    测试用户
    """

    def __init__(self, environment):
        super().__init__(environment)

    @task
    def task(self):
        self.environment.c_runner.call(self)
