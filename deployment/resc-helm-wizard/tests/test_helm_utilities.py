# Standard Library
import subprocess
import sys
import unittest.mock as mock
from unittest.mock import patch

# First Party
from resc_helm_wizard import constants
from resc_helm_wizard.helm_utilities import (
    add_helm_repository,
    get_version_from_downloaded_chart,
    get_version_from_installed_chart,
    install_or_upgrade_helm_release,
    is_chart_version_already_installed,
    update_helm_repository
)

sys.path.insert(0, "src")


@patch("subprocess.check_output")
@patch("logging.Logger.info")
def test_install_or_upgrade_helm_release_success(mock_info_log, mock_check_output):
    expected_output = b"installation successful"
    mock_check_output.return_value = expected_output
    expected_info_log = "installation successful"
    actual_output = install_or_upgrade_helm_release(action="install")
    assert actual_output is True
    mock_info_log.assert_called_with(expected_info_log)


@patch("logging.Logger.error")
def test_install_or_upgrade_helm_release_failure(mock_error_log):
    expected_error_log = f"An error occurred during {constants.CHART_NAME} deployment"
    with mock.patch("subprocess.check_output") as mock_check_output:
        mock_check_output.side_effect = subprocess.CalledProcessError(returncode=1, cmd="my command")
        actual_output = install_or_upgrade_helm_release(action="install")
        assert mock_check_output.called
        assert actual_output is False
        mock_error_log.assert_called_with(expected_error_log)


@patch("resc_helm_wizard.helm_utilities.get_version_from_downloaded_chart")
@patch("resc_helm_wizard.helm_utilities.get_version_from_installed_chart")
def test_is_chart_version_already_installed_is_true(get_version_from_installed_chart,
                                                    get_version_from_downloaded_chart):
    get_version_from_installed_chart.return_value = "1.0.0"
    get_version_from_downloaded_chart.return_value = "1.0.0"
    already_installed = is_chart_version_already_installed()
    get_version_from_installed_chart.assert_called_once_with()
    get_version_from_downloaded_chart.assert_called_once_with()
    assert already_installed is True


@patch("resc_helm_wizard.helm_utilities.get_version_from_downloaded_chart")
@patch("resc_helm_wizard.helm_utilities.get_version_from_installed_chart")
def test_is_chart_version_already_installed_is_false(get_version_from_installed_chart,
                                                     get_version_from_downloaded_chart):
    get_version_from_installed_chart.return_value = "1.0.0"
    get_version_from_downloaded_chart.return_value = "1.0.1"
    already_installed = is_chart_version_already_installed()
    get_version_from_installed_chart.assert_called_once_with()
    get_version_from_downloaded_chart.assert_called_once_with()
    assert already_installed is False


@patch("subprocess.check_output")
def test_get_version_from_installed_chart_success(mock_check_output):
    expected_output = b'[{"name":"resc","namespace":"resc","revision":"1",' \
                      b'"updated":"2023-03-30 10:16:56.211749 +0200 CEST","status":"deployed",' \
                      b'"chart":"resc-1.1.0","app_version":"1.1.0"}]\n'
    mock_check_output.return_value = expected_output
    actual_output = get_version_from_installed_chart()
    assert actual_output == "1.1.0"


@patch("subprocess.check_output")
def test_get_version_from_installed_chart_failure(mock_check_output):
    expected_output = b'{}'
    mock_check_output.return_value = expected_output
    actual_output = get_version_from_installed_chart()
    assert actual_output is None


@patch("subprocess.check_output")
def test_get_version_from_downloaded_chart_success(mock_check_output):
    expected_output = b'[{"name":"resc-helm-repo/resc","version":"1.1.0","app_version":"1.1.0",' \
                      b'"description":"A Helm chart for the Repository Scanner"}]\n'
    mock_check_output.return_value = expected_output
    actual_output = get_version_from_downloaded_chart()
    assert actual_output == "1.1.0"


@patch("subprocess.check_output")
def test_get_version_from_downloaded_chart_failure(mock_check_output):
    expected_output = b'{}'
    mock_check_output.return_value = expected_output
    actual_output = get_version_from_downloaded_chart()
    assert actual_output is None


@patch("subprocess.run")
def test_add_helm_repository_success(mock_check_output):
    cmd = ["helm", "repo", "add", constants.HELM_REPO_NAME, constants.RESC_HELM_REPO_URL]
    add_helm_repository()
    assert mock_check_output.called
    mock_check_output.assert_called_once_with(cmd, check=True)


@patch("logging.Logger.error")
def test_add_helm_repository_failure(mock_error_log):
    cmd = ["helm", "repo", "add", constants.HELM_REPO_NAME, constants.RESC_HELM_REPO_URL]
    expected_error_log = "An error occurred while adding the helm repository"
    with mock.patch("subprocess.run") as mock_check_output, \
            mock.patch("sys.exit") as mock_sys_exit:
        mock_check_output.side_effect = subprocess.CalledProcessError(returncode=1, cmd=cmd)
        add_helm_repository()
        assert mock_check_output.called
        mock_error_log.assert_called_with(expected_error_log)
        mock_check_output.assert_called_once_with(cmd, check=True)
        mock_sys_exit.assert_called_once_with(1)


@patch("subprocess.run")
def test_update_helm_repository_success(mock_check_output):
    cmd = ["helm", "repo", "update", constants.HELM_REPO_NAME]
    update_helm_repository()
    assert mock_check_output.called
    mock_check_output.assert_called_once_with(cmd, check=True)


@patch("logging.Logger.error")
def test_update_helm_repository_failure(mock_error_log):
    cmd = ["helm", "repo", "update", constants.HELM_REPO_NAME]
    expected_error_log = "An error occurred while updating the helm repository"
    with mock.patch("subprocess.run") as mock_check_output, \
            mock.patch("sys.exit") as mock_sys_exit:
        mock_check_output.side_effect = subprocess.CalledProcessError(returncode=1, cmd=cmd)
        update_helm_repository()
        assert mock_check_output.called
        mock_error_log.assert_called_with(expected_error_log)
        mock_check_output.assert_called_once_with(cmd, check=True)
        mock_sys_exit.assert_called_once_with(1)