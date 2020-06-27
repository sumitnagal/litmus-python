"""Script for Gathering all except master nodes and terminate them one by one. """
import argparse
import logging
import os
import sys
import time

from boto3 import Session
from chaostest.aws.awsutils import AwsUtils
from chaostest.utils.chasotoolkit_utils import ChaosUtils, chaos_result_decorator, ChaosAction, \
    environment_params_for_test, update_test_chaos_params

__author__ = 'Vijay Thomas'

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(asctime)s %(levelname)-2s] [%(module)s:%(lineno)s] %(message)s",
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("chaostoolkit.log"),
        logging.StreamHandler(sys.stdout)
    ]
    )
# Enable below line if boto stream response has to be observed in logs
# boto3.set_stream_logger(name='botocore')

parser = argparse.ArgumentParser()
parser.add_argument("-accnumber",
                    action=ChaosAction,
                    required=False,
                    default='331419223978',
                    dest='aws_account',
                    help="AWS account under usage")
parser.add_argument("-local",
                    action='store_true',
                    required=False,
                    default=False,
                    dest='local',
                    help="AWS local test")
parser.add_argument("-role",
                    action=ChaosAction,
                    required=False,
                    default='chaosec2experiment',
                    dest='aws_role',
                    help="AWS account under usage")
parser.add_argument("-region",
                    action=ChaosAction,
                    dest='aws_region',
                    required=False,
                    default='us-west-2',
                    help="AWS region under usage")
parser.add_argument("-az",
                    action=ChaosAction,
                    required=False,
                    default='us-west-2c',
                    dest='aws_az',
                    help="AWS aplication zone under usage")
parser.add_argument("-chaosFile",
                    action=ChaosAction,
                    default="ec2-delete.json",
                    dest="file",
                    help="Chaos file to chose for execution"
                    )
parser.add_argument("-boto3Resource",
                    action=ChaosAction,
                    required=False,
                    dest="aws_resource",
                    default="ec2-iks",
                    help="Chose aws resource to initialize boto3")
parser.add_argument("-verifySSL",
                    required=False,
                    default="false",
                    action=ChaosAction,
                    dest='KUBERNETES_VERIFY_SSL',
                    help="Kubernetes client ignore SSL")
parser.add_argument("-kubeConfig",
                    required=False,
                    default="",
                    dest='kubeconfig',
                    help="Kubernetes client ignore SSL")
parser.add_argument("-kubeContext",
                    required=False,
                    default=os.environ.get("KUBECONFIG", ""),
                    dest='kubeContext',
                    help="Kubernetes client ignore SSL")
parser.add_argument('-report', action=ChaosAction,
                    dest='report',
                    default="false",
                    help='Option to upload the result to report server')
parser.add_argument('-report_endpoint', action=ChaosAction,
                    dest='report_endpoint',
                    default="none",
                    help='Endpoint where the report kubernetes will be uploaded')
parser.add_argument("-namespace", action=ChaosAction,
                    required=False,
                    default="dev-reliabilityiks3-usw2-qal",
                    dest="name_space",
                    help="namespace for application"
                    )
parser.add_argument("-experiment", action=ChaosAction,
                    required=False,
                    dest="exp",
                    default="experiment-aws",
                    help="Experiment yaml name"
                    )
parser.add_argument("-testNamespace",
                    required=False,
                    default="dev-reliabilityiks3-usw2-qal",
                    dest='test_namespace',
                    help="Namespace on which chaos results will be persisted")
parser.add_argument("-appPodPattern",
                    required=False,
                    default="appd-deployment",
                    dest='app_pod_pattern',
                    help="pod name patterns from which nodes have to be picked for deletion")
parser.add_argument('-app', action=ChaosAction,
                    required=False,
                    dest='app_endpoint',
                    default="localhost",
                    help='Store the application health endpoint')


args = parser.parse_args()
aws_account_number = args.aws_account
aws_account_role = args.aws_role
aws_region = args.aws_region
aws_application_zone = args.aws_az
chaos_file = args.file
aws_boto3_resource = args.aws_resource
local = args.local
verifySSL = args.KUBERNETES_VERIFY_SSL
kubecontext = args.kubeContext
experiment = args.exp
test_namespace = args.test_namespace
namespace = args.name_space
pod_name_pattern = args.app_pod_pattern
report = args.report
report_endpoint = args.report_endpoint

INVALID_RESOURCE = "Not supported Resource"


def aws_resource(aws_resource_with_env: str, session: Session, namespace: str, pod_identifier_pattern):
    aws_resources = {
        "ec2-iks": AwsUtils.ec2_detach_eks(session, kubecontext, namespace, pod_identifier_pattern)
    }
    return aws_resources.get(aws_resource_with_env, lambda: "Not supported Resource")


@chaos_result_decorator
def execute_test_kill_worker_ec2(account_number: str = None, account_role: str = None,
                                 region: str = None,
                                 file: str = None, experiment_name=None):
    test_result = False
    if 'CHAOSENGINE' in os.environ.keys():
        experiment_name = os.environ['CHAOSENGINE'] + '-' + experiment_name

    timestamp = str(int(time.time() * 1000))
    result_name = experiment_name + "-" + timestamp

    # noinspection PyBroadException
    try:
        if local:
            session = AwsUtils.aws_init_local(account_number)
        else:
            session = AwsUtils.aws_init_by_role(account_number, account_role, region)
        instance_id = aws_resource("ec2-iks", session, namespace, pod_name_pattern)

        chaos_utils = ChaosUtils()
        update_test_chaos_params("EC2_INSTANCE_ID", instance_id)
        aws_arn = "arn:aws:iam::" + account_number + ":role/" + aws_account_role
        update_test_chaos_params("AWS_ARN", aws_arn)
        test_result = chaos_utils.run_chaos_engine(file, environment_params_for_test, report, report_endpoint)
    except Exception as ex:
        logger.error("Tests failed , exception is " + str(ex))


execute_test_kill_worker_ec2(aws_account_number, aws_account_role, aws_region, chaos_file, experiment)
