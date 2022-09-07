import os
import time
import pytz
import requests

from auto_stop_workers import start_worker, stop_worker
from prometheus_api_client import PrometheusConnect

utc = pytz.UTC

NUM_PROCESSED_SUBMISSIONS = "num_processed_submissions"
NUM_SUBMISSIONS_IN_QUEUE = "num_submissions_in_queue"
PROMETHEUS_URL = "https://monitoring.eval.ai/prometheus/"

# Eval AI related credentials
evalai_endpoint = os.environ.get("API_HOST_URL")
authorization_header = {
    "Authorization": "Bearer {}".format(os.environ.get("AUTH_TOKEN"))
}

prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)


def execute_get_request(url):
    response = requests.get(url, headers=authorization_header)
    return response.json()


def get_challenges():
    all_challenge_endpoint = "{}/api/challenges/challenge/all/all/all".format(
        evalai_endpoint  # Gets all challenges
    )
    response = execute_get_request(all_challenge_endpoint)

    return response


def get_queue_length(queue_name):
    num_processed_submissions = int(
        prom.custom_query(
            f"num_processed_submissions{{queue_name='{queue_name}'}}"
        )[0]["value"][1]
    )
    num_submissions_in_queue = int(
        prom.custom_query(
            f"num_submissions_in_queue{{queue_name='{queue_name}'}}"
        )[0]["value"][1]
    )
    return num_submissions_in_queue - num_processed_submissions


def get_queue_length_by_challenge(challenge):
    queue_name = challenge["queue"]
    return get_queue_length(queue_name)


def increase_or_decrease_workers(challenge):
    try:
        queue_length = get_queue_length_by_challenge(challenge)
    except Exception as _e:  # noqa: F841
        print(
            "Unable to get the queue length for challenge ID: {}. Skipping.".format(
                challenge["id"]
            )
        )
        return
    print(challenge["workers"], queue_length)
    if queue_length == 0:
        if challenge["workers"] is not None and int(challenge["workers"]) > 0:
            # Worker > 0 and Queue = 0 - Stop
            # stop worker
            stop_worker(challenge["id"])
            print("Stopped worker for challenge: {}".format(challenge["id"]))
        else:
            # Worker = 0 and Queue = 0
            print(
                "No workers and queue messages found for challenge: {}. Skipping.".format(
                    challenge["id"]
                )
            )

    else:
        # Worker = 0, Queue > 0
        if challenge["workers"] is None or int(challenge["workers"]) == 0:
            # start worker
            start_worker(challenge["id"])
            print("Started worker for challenge: {}".format(challenge["id"]))
        else:
            # Worker > 0 and Queue > 0
            print(
                "Existing workers and pending queue messages found for challenge: {}. Skipping.".format(
                    challenge["id"]
                )
            )


# TODO: Factor in limits for the APIs
def increase_or_decrease_workers_for_challenges(response):
    for challenge in response["results"]:
        if (
            not challenge["is_docker_based"]
            and not challenge["remote_evaluation"]
        ):
            if str(challenge["id"]) == "683":
                increase_or_decrease_workers(challenge)
                time.sleep(2)


# Cron Job
def start_job():
    response = get_challenges()
    increase_or_decrease_workers_for_challenges(response)
    next_page = response["next"]
    while next_page is not None:
        response = execute_get_request(next_page)
        increase_or_decrease_workers_for_challenges(response)
        next_page = response["next"]


if __name__ == "__main__":
    print("Starting worker auto scaling script")
    start_job()
    print("Quitting worker auto scaling script!")
