#!/usr/bin/env python3
# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SPDX-License-Identifier: MIT


import os
import argparse
from typing import List
from dotenv import load_dotenv
import asyncio

from autogen_agentchat.messages import TextMessage

from ..utils import find_dotenv_file
from ..utils.cli_inputs import load_cli_content
from ..utils.agent_callbacks import (
    preprocess_messages_logging,
    postprocess_messages_logging,
)
from ..utils.plan_grounding import check_plan_grounding
from ..utils.result_extractors import extract_hunt_plan

from . import plan_hunt


def main() -> None:
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Given the outputs of all the other Prepare-phase agents, create an actionable plan for the hunt."
    )
    parser.add_argument("-e", "--environment", help="Path to specific .env file to use")
    parser.add_argument(
        "-r",
        "--research",
        help="Path to the research document (markdown file)",
        required=True,
    )
    parser.add_argument(
        "-y", "--hypothesis", help="The hunting hypothesis", required=True
    )
    parser.add_argument(
        "-a",
        "--able_info",
        help="Path to the ABLE information file (Actor, Behavior, Location, Evidence), or the ABLE text itself if not a path",
        required=False,
        default=None,
    )
    parser.add_argument(
        "-d",
        "--data_discovery",
        help="Path to the data discovery output file from previous agents",
        required=False,
        default=None,
    )
    parser.add_argument(
        "-l",
        "--local-data",
        help="Path to the local data document (markdown file)",
        required=False,
        default=None,
    )
    parser.add_argument(
        "-c",
        "--local_context",
        help="Path to the local context file (additional context to consider), or the context text itself if not a path",
        required=False,
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
        default=False,
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Skip user feedback and automatically accept the generated hunt plan"
    )
    parser.add_argument(
        "--allow-ungrounded-plan",
        action="store_true",
        help=(
            "Accept a hunt plan even when grounding checks fail (indices not in "
            "the discovery report, non-executable SPL). Without this flag a "
            "plan that fails grounding checks is a hard error."
        )
    )
    parser.add_argument(
        "--debug-agents",
        action="store_true",
        help="Enable agent debug logging to msgs.txt and results.txt"
    )
    args = parser.parse_args()

    # Load environment variables
    if args.environment:
        # Use the specified .env file
        dotenv_path = args.environment
        if not os.path.exists(dotenv_path):
            print(f"Error: Specified environment file '{dotenv_path}' not found")
            exit(1)
        load_dotenv(dotenv_path)
    else:
        # Search for .env file
        dotenv_path = find_dotenv_file()
        if dotenv_path:
            load_dotenv(dotenv_path)
        else:
            print("Warning: No .env file found in current or parent directories")

    # Read the contents of the research document
    try:
        with open(args.research, "r", encoding="utf-8") as file:
            research_data = file.read()
    except FileNotFoundError:
        print(f"Error: Research document '{args.research}' not found")
        exit(1)
    except Exception as e:
        print(f"Error reading research document: {e}")
        exit(1)

    # Read the contents of the ABLE information if provided (file path or
    # inline value; a path-shaped value that does not exist is an error)
    able_info = load_cli_content(args.able_info, "ABLE information")

    # Read the contents of the data discovery information if provided
    data_discovery = None
    if args.data_discovery:
        try:
            with open(args.data_discovery, "r", encoding="utf-8") as file:
                data_discovery = file.read()
        except FileNotFoundError:
            print(f"Error: Data discovery file '{args.data_discovery}' not found")
            exit(1)
        except Exception as e:
            print(f"Error reading data discovery information: {e}")
            exit(1)

    # Read the contents of the local data document if provided
    local_data = None
    if args.local_data:
        try:
            with open(args.local_data, "r", encoding="utf-8") as file:
                local_data = file.read()
        except FileNotFoundError:
            print(f"Error: Local data document '{args.local_data}' not found")
            exit(1)
        except Exception as e:
            print(f"Error reading local data document: {e}")
            exit(1)

    # Read the contents of the local context if provided (file path or
    # inline value; a path-shaped value that does not exist is an error)
    local_context = load_cli_content(args.local_context, "Local context")

    messages: List[TextMessage] = list()
    debug_agents_opts = dict()

    if args.debug_agents:
        debug_agents_opts = {
            "msg_preprocess_callback": preprocess_messages_logging,
            "msg_preprocess_kwargs": {"agent_id": "hunt-planner"},
            "msg_postprocess_callback": postprocess_messages_logging,
            "msg_postprocess_kwargs": {"agent_id": "hunt-planner"},
        }

    while True:
        # Run the hypothesizer asynchronously
        data_sources = asyncio.run(
            plan_hunt(
                research_document=research_data,
                local_data_document=local_data or "",
                hypothesis=args.hypothesis,
                able_info=able_info or "",
                data_discovery=data_discovery or "",
                local_context=local_context or "",
                verbose=args.verbose,
                previous_run=messages,
                **debug_agents_opts,
            )
        )

        # Extract hunt plan using the centralized extractor
        hunt_plan = extract_hunt_plan(data_sources)

        # Deterministic grounding check (fork fix, finding 10): flag indices
        # the plan cites that the discovery report never mentions, and plan
        # queries that violate the pinned executable-SPL rules. Default is a
        # hard error — the tool refuses to hand the hunter fabricated data
        # sources; --allow-ungrounded-plan downgrades it to a warning.
        grounding_report = check_plan_grounding(hunt_plan, data_discovery or "")
        if not grounding_report.ok:
            violations = []
            if grounding_report.undiscovered_indices:
                violations.append(
                    "Indices cited but not in the discovery report: "
                    + ", ".join(grounding_report.undiscovered_indices)
                )
            for query in grounding_report.suspicious_queries:
                violations.append(f"Not executable as written: {query[:160]}")

            if args.allow_ungrounded_plan:
                print(
                    "GROUNDING WARNING: the plan references data not present in the "
                    "data discovery report — treat affected queries as unverified."
                )
                for violation in violations:
                    print(f"  {violation}")
            else:
                print(
                    "GROUNDING ERROR: the plan references data not present in the "
                    "data discovery report, so the hunt would run against "
                    "unverified or fabricated data sources. Refusing to accept "
                    "the plan.",
                )
                for violation in violations:
                    print(f"  {violation}")
                print(
                    "Re-run with a data discovery report that covers the required "
                    "indices, or pass --allow-ungrounded-plan to accept the plan "
                    "anyway."
                )
                exit(1)

        print(f"Hunt plan:\n{'*' * 50}\n{hunt_plan}\n{'*' * 50}")
        
        if args.no_feedback:
            print("Skipping user feedback (--no-feedback enabled)")
            break
        
        feedback = input(
            "Please provide your feedback on the plan (or press Enter to approve it): "
        )

        if feedback.strip():
            # If feedback is provided, add it to the messages and loop back to
            # the research team for further refinement
            messages = [
                TextMessage(
                    content=f"The current plan draft is: {hunt_plan}\n", source="user"
                ),
                TextMessage(content=f"User feedback: {feedback}\n", source="user"),
            ]
        else:
            break


if __name__ == "__main__":
    main()
