# Reproducible environment for the full RTL-to-GDSII flow.
#
# The synthesis stage (Yosys) is intentionally lightweight and runs in plain
# CI (see .github/workflows/ci.yml). This image additionally layers on
# OpenROAD + KLayout for the place-and-route stage (flow/pnr/openroad_flow.tcl),
# which needs a real PDK and is too heavy to run in every CI job.
FROM openroad/flow-ubuntu22.04-builder:latest

RUN apt-get update -qq && \
    apt-get install -y -qq \
        yosys \
        klayout \
        python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "-m", "scheduler.job_scheduler"]
