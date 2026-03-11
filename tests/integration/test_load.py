import os
import tempfile
import uuid

import pytest

import alphatrion as alpha


@pytest.mark.asyncio
async def test_save_and_load_dataset():
    # Ensure valid working directory before initialization
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    os.chdir(project_root)

    team_id = uuid.uuid4()
    alpha.init(
        team_id=team_id,
        user_id=uuid.uuid4(),
    )

    # Use tempfile to avoid working directory issues
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files for upload
        file_path = os.path.join(tmpdir, "test_dataset.txt")
        with open(file_path, "w") as f:
            f.write("This is a test dataset file.")

        file_path2 = os.path.join(tmpdir, "test_dataset2.txt")
        with open(file_path2, "w") as f:
            f.write("This is another test dataset file.")

        # Upload dataset
        dataset_id = await alpha.log_dataset(
            name="test_dataset",
            data_or_path=[file_path, file_path2],
        )

    # Download dataset to a new temp directory
    with tempfile.TemporaryDirectory() as download_dir:
        await alpha.load_dataset(id=dataset_id, output_dir=download_dir)

        # Verify files were downloaded
        assert os.path.exists(os.path.join(download_dir, "test_dataset.txt"))
        assert os.path.exists(os.path.join(download_dir, "test_dataset2.txt"))

        # Verify content
        with open(os.path.join(download_dir, "test_dataset.txt")) as f:
            assert f.read() == "This is a test dataset file."
