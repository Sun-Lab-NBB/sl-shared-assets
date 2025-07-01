from pathlib import Path

from sl_shared_assets import Server, JupyterServerManager

# Initialize server connection
server = Server(Path("/home/cyberaxolotl/Data/server_credentials.yaml"))

# Create Jupyter manager
jupyter_mgr = JupyterServerManager(
    server=server, conda_environment="jupyter", working_directory=server.processed_data_root.joinpath("temp")
)

# Launch a Jupyter server
connection_info = jupyter_mgr.launch_jupyter_server(
    port=9999,
    job_name="interactive_analysis",
    notebook_dir=server.processed_data_root,
    cpus_to_use=8,
    ram_gb=32,
    time_limit=5,  # 5 minutes
)


# RUN THIS NOW:
if __name__ == "__main__":
    # Get connection details
    print(f"Jupyter is running on: {connection_info.compute_node}")
    print(f"Port: {connection_info.port}")
    print(f"Token: {connection_info.token}")
    print(f"Direct URL: {connection_info.connection_url}")

    # Get SSH tunnel command for local access
    tunnel_cmd = jupyter_mgr.get_ssh_tunnel_command(connection_info)
    print(f"\nTo access locally, run this in a terminal:")
    print(tunnel_cmd)
    print(f"\nThen open: {connection_info.localhost_url}")

    input("Enter to shutdown")

    # When done, stop the server
    jupyter_mgr.stop_jupyter_server(connection_info.job_id)

    # Close server connection
    server.close()
