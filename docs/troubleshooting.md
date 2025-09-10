# Troubleshooting

## Common Issues and Solutions

1. Failed to push the artifacts to the artifact registry:
   - Ensure that the `ARTIFACT_REGISTRY_URL` environment variable is correctly set in your `.env` file, it looks like:
     ```
     ARTIFACT_REGISTRY_URL=https://gcr.io/alphatrion/
     ```
   - Verify that you have the necessary permissions to push to the specified registry and the repository exists.
   - For cloud user and local deployment, we use credential helper to authenticate. For example for google cloud, please make sure you have installed Google Cloud SDK and run the following command to configure Docker authentication:
     ```bash
     gcloud auth configure-docker gcr.io
     ```