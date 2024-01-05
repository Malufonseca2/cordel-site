#!/usr/bin/python3
import oci
from datetime import datetime, timedelta
from argparse import ArgumentParser
from logprint import LogPrint
from os import path
from sys import argv
import json

parser = ArgumentParser(description="Retorna status dos túneis vpn do Compartment ID e região informados.")
parser.add_argument("--compartment_id", required=True, help="Compartment OCID")
parser.add_argument("--region", required=True, help="OCI Region")
parser.add_argument("--metric", required=True, help="Metric Name")
parser.add_argument('--loglevel', dest = 'loglevel', default = 'ERROR', help = 'Debug level. DEBUG/INFO/WARNING/ERROR/CRITICAL')
parser.add_argument('--no-verbose', dest = 'verbose', action = 'store_false', help = 'Dont show any logs on screen')
parser.add_argument('--verbose', dest = 'verbose', action = 'store_true')
parser.set_defaults(verbose=True)

args = parser.parse_args()

LOGFILE = "/tmp/%s.log" % path.basename(argv[0])
logger = LogPrint(echo=args.verbose, logfile=LOGFILE, loglevel=args.loglevel.upper())

def initialize_oci_config(region):
    try:
        # Tenta inicializar as configurações da OCI
        config = {
        "user": 'ocid1.user.oc1..aaaaaaaaiitqtrimhb3ygrux5jcib5b4icy4mjzwaon62tqitdtjvif7vyrq',
        "key_file": '~/Documents/OCI/oci_api_key.pem',
        "fingerprint": '47:78:66:99:cd:4c:59:d6:8a:fd:59:6b:f2:7b:5d:e7',
        "tenancy": 'ocid1.tenancy.oc1..aaaaaaaand4xcanpaqckfaohjrk66dccmt65my7m7ckz5p3n2hf5ccza6skq',
        "region": region
        }
        oci.config.validate_config(config)
        return config
    except oci.exceptions.ConfigFileInvalid as e:
        logger.error(f"Erro: Arquivo de configuração inválido. Verifique o conteúdo do arquivo {e.filename}.")

def get_monitoring_client(config):
    return oci.monitoring.MonitoringClient(config)

def list_metrics(monitoring_client, compartment_id, metrics):
    return monitoring_client.list_metrics(
        compartment_id=compartment_id,
        list_metrics_details=oci.monitoring.models.ListMetricsDetails(
            name=metrics,
            namespace="oci_vpn"
        ),
        opc_request_id="",
        page="",
        limit=765,
        compartment_id_in_subtree=False
    ).data

def summarize_metrics_data(monitoring_client, compartment_id, resource_name, start_time_str, end_time_str, metrics):
    query = f"{metrics}[1m]{{resourceName = \"{resource_name}\"}}.last()"

    return monitoring_client.summarize_metrics_data(
        compartment_id=compartment_id,
        summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
            namespace="oci_vpn",
            query=query,
            start_time=start_time_str,
            end_time=end_time_str
        ),
        opc_request_id="",
        compartment_id_in_subtree=False,
    ).data

def process_metrics_data(metrics_list, monitoring_client, compartment_id, start_time_str, end_time_str, metrics):
    result_list = []

    for metric in metrics_list:
        resource_name = metric.dimensions['resourceName']
        public_ip = metric.dimensions['publicIp']
        namespace = metric.namespace
        metric_name = metric.name

        smdr = summarize_metrics_data(monitoring_client, compartment_id, resource_name, start_time_str, end_time_str, metrics)

        value = smdr[0].aggregated_datapoints[0].value
        result_list.append({"resource_name": resource_name, "name": metric_name, "value": value,
                            "namespace": namespace, "public_ip": public_ip})
        
    result_json = {"resource": result_list}
    result = json.dumps(result_json)
        
    return result

def main():
    compartment_id = args.compartment_id
    region = args.region
    metrics = args.metric

    config = initialize_oci_config(region)
    
    if config:
        monitoring_client = get_monitoring_client(config)

        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=1)

        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        metrics_list = list_metrics(monitoring_client, compartment_id, metrics)
        result_list = process_metrics_data(metrics_list, monitoring_client, compartment_id, start_time_str, end_time_str, metrics)
        print(json.dumps(json.loads(result_list), sort_keys=True))

        #logger.info(result_list)
    else:
        logger.error("Falha ao inicializar as configurações da OCI. Consulte os erros acima para obter detalhes.")
        
main()
