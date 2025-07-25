import os
import re
from dotenv import load_dotenv
import json
from openai import AzureOpenAI

# Load environment variables
load_dotenv()


client = AzureOpenAI(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

def visualize(data):
    json = f"{data}"
    prompt = f"""   You are a data assistant designed to build visualizations.

                    Users will paste json data and you will respond with configurations for four Chart.js components, following these guidelines:

                    1. Chart Structure: Generate configurations for exactly four charts, with each chart corresponding to a different section of data.

                    2. Chart Type Selection: For each chart, choose between a line chart or a bar chart based on the data characteristics. Do not use radar or pie charts.

                    3. Data Integrity: Ensure every data point provided is included in the charts. Double-check that no data is omitted, and all values are represented accurately.

                    4. Output Format: Present the results as a pure JSON. Do not include any preamble, explanation, code blocks, or additional wrappers.

                    5. Verification: Before finalizing, verify that all provided data points are accounted for in the JSON output.

                    Here is an example of your output JSON Format:
                    {"""{"charts": [
                    {
                        "type": "chart_type",
                        "data": {
                        "labels": ["label1", "label2", "label3"],
                        "datasets": [
                            {
                            "label": "dataset_label1",
                            "data": ["value1", "value2", "value3"],
                            "fill": false
                            },
                            {
                            "label": "dataset_label2",
                            "data": ["value1", "value2", "value3"],
                            "fill": false
                            }
                        ]
                        },
                        "options": {
                        "responsive": true,
                        "plugins": {
                            "legend": {

                                                 "position": "top"
                            },
                            "title": {
                            "display": true,
                            "text": "chart_title"
                            },
                            "colors": {
                            "forceOverride": true
                            }
                        },
                        "scales": {
                            "x": {
                            "beginAtZero": true
                            },
                            "y": {
                            "beginAtZero": true
                            }
                        }
                        }
                    }
                    ]}"""}
                """
    
    response = client.chat.completions.create(
        model=os.getenv('DEPLOYMENT_NAME'),
        messages=[{"role": "system", "content": prompt},
                  {"role": "user", "content": json}]
        )
    out = response.choices[0].message.content
    with open("viz.json", 'w') as file:
        file.write(out)
    return out

# data = """
#     {
#     "metrics": {
#         "release_scope": {
#             "Target Customers": {
#                 "45.1.15.0": "H&M",
#                 "45.1.16.0": "BP",
#                 "45.1.17.0": "BHEL"
#             },
#             "Release Epics": {
#                 "45.1.15.0": {
#                     "Total": 11,
#                     "Open": 0
#                 },
#                 "45.1.16.0": {
#                     "Total": 11,
#                     "Open": 0
#                 },
#                 "45.1.17.0": {
#                     "Total": 19,
#                     "Open": 0
#                 }
#             },
#             "Release PIRs": {
#                 "45.1.15.0": {
#                     "Total": 0,
#                     "Open": 0
#                 },
#                 "45.1.16.0": {
#                     "Total": 93,
#                     "Open": 0
#                 },
#                 "45.1.17.0": {
#                     "Total": 108,
#                     "Open": 0
#                 }
#             },
#             "SFDC Defects Fixed": {
#                 "45.1.15.0": {
#                     "ATLs Fixed": 83,
#                     "BTLs Fixed": 26
#                 },
#                 "45.1.16.0": {
#                     "ATLs Fixed": 88,
#                     "BTLs Fixed": 41
#                 },
#                 "45.1.17.0": {
#                     "ATLs Fixed": 100,
#                     "BTLs Fixed": 26
#                 }
#             }
#         },
#         "critical_metrics": {
#             "Delivery Against Requirements": {
#                 "45.1.15.0": {
#                     "Value": 100,
#                     "Status": "NO RISK"
#                 },
#                 "45.1.16.0": {
#                     "Value": null,
#                     "Status": "NO RISK"
#                 },
#                 "45.1.17.0": {
#                     "Value": 100,
#                     "Status": "NO RISK"
#                 }
#             },
#             "System / Solution Test Metrics": {
#                 "45.1.15.0": {
#                     "Total": 287,
#                     "Open": 1,
#                     "Status": null
#                 },
#                 "45.1.16.0": {
#                     "Total": 1017,
#                     "Open": 2,
#                     "Status": null
#                 },
#                 "45.1.17.0": {
#                     "Total": 1250,
#                     "Open": 8,
#                     "Status": null
#                 }
#             },
#             "System / Solution Test Coverage": {
#                 "45.1.15.0": {
#                     "Value": 90,
#                     "Status": "MEDIUM RISK"
#                 },
#                 "45.1.16.0": {
#                     "Value": 96,
#                     "Status": "MEDIUM RISK"
#                 },
#                 "45.1.17.0": {
#                     "Value": 90,
#                     "Status": "MEDIUM RISK"
#                 }
#             },
#             "System / Solution Test Pass Rate": {
#                 "45.1.15.0": {
#                     "Value": 93,
#                     "Status": "MEDIUM RISK"
#                 },
#                 "45.1.16.0": {
#                     "Value": 92,
#                     "Status": "MEDIUM RISK"
#                 },
#                 "45.1.17.0": {
#                     "Value": 93,
#                     "Status": "MEDIUM RISK"
#                 }
#             },
#             "Security Test Metrics": {
#                 "45.1.15.0": {
#                     "Total": 0,
#                     "Open": 0,
#                     "Status": "NO RISK"
#                 },
#                 "45.1.16.0": {
#                     "Total": 0,
#                     "Open": 0,
#                     "Status": "NO RISK"
#                 },
#                 "45.1.17.0": {
#                     "Total": 20,
#                     "Open": 0,
#                     "Status": "NO RISK"
#                 }
#             },
#             "Performance / Load Test Metrics": {
#                 "45.1.15.0": {
#                     "Total": 0,
#                     "Open": 0,
#                     "Status": "NO RISK"
#                 },
#                 "45.1.16.0": {
#                     "Total": 0,
#                     "Open": 0,
#                     "Status": "NO RISK"
#                 },
#                 "45.1.17.0": {
#                     "Total": 12,
#                     "Open": 25,
#                     "Status": "NO RISK"
#                 }
#             }
#         },
#         "health_trends": {
#             "Unit Test Coverage": {
#                 "45.1.15.0": {
#                     "Criteria": ">= 80%",
#                     "Previous": "20%",
#                     "Current": "25%",
#                     "Status": "WIP",
#                     "Summary": "This is an ongoing effort with ETA of Q3 2026"
#                 },
#                 "45.1.16.0": {
#                     "Criteria": ">= 80%",
#                     "Previous": "25%",
#                     "Current": "40%",
#                     "Status": "WIP",
#                     "Summary": "This is an ongoing effort with ETA of Q3 2026"
#                 },
#                 "45.1.17.0": {
#                     "Criteria": ">= 80%",
#                     "Previous": "20%",
#                     "Current": "25%",
#                     "Status": "WIP",
#                     "Summary": "This is an ongoing effort with ETA of Q3 2026"
#                 }
#             },
#             "Automation Test Coverage": {
#                 "45.1.15.0": {
#                     "Criteria": ">= 85%",
#                     "Previous": "50%",
#                     "Current": "50%",
#                     "Status": "WIP",
#                     "Summary": "This is an ongoing effort with ETA of Q3 2026"
#                 },
#                 "45.1.16.0": {
#                     "Criteria": ">= 85%",
#                     "Previous": "50%",
#                     "Current": "60%",
#                     "Status": "WIP",
#                     "Summary": "This is an ongoing effort with ETA of Q3 2026"
#                 },
#                 "45.1.17.0": {
#                     "Criteria": ">= 85%",
#                     "Previous": "50%",
#                     "Current": "50%",
#                     "Status": "WIP",
#                     "Summary": "This is an ongoing effort with ETA of Q3 2026"
#                 }
#             }
#         }
#     }"""
# out = visualize(data)
# print(out)

# with open("viz.json", 'w') as file:
#     file.write(out)


