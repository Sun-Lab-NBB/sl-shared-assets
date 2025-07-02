from pathlib import Path

from sl_shared_assets import Server, JupyterJob

if __name__ == "__main__":
    # Initializes server connection
    server = Server(Path("/home/cyberaxolotl/Data/server_credentials.yaml"))

    # Launches a Jupyter server
    job: JupyterJob = server.launch_jupyter_server(
        job_name="interactive_analysis",
        conda_environment="jupyter",
        notebook_directory=server.processed_data_root,
        cpus_to_use=8,
        ram_gb=32,
        time_limit=30,  # 30 minutes
    )

    job.print_connection_info()

    input("Enter to shutdown")

    # When done, stop the server
    server.abort_job(job)

    # Closes server connection
    server.close()
