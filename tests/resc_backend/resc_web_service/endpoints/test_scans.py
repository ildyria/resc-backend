# Standard Library
import unittest
from datetime import UTC, datetime
from unittest.mock import ANY, patch

# Third Party
from fastapi.testclient import TestClient

# First Party
from resc_backend.constants import (
    RWS_ROUTE_DETECTED_RULES,
    RWS_ROUTE_FINDINGS,
    RWS_ROUTE_SCANS,
    RWS_VERSION_PREFIX,
)
from resc_backend.db.model import DBfinding, DBrepository, DBrule, DBscan
from resc_backend.resc_web_service.api import app
from resc_backend.resc_web_service.dependencies import requires_auth, requires_no_auth
from resc_backend.resc_web_service.schema.finding import FindingRead
from resc_backend.resc_web_service.schema.finding_status import FindingStatus
from resc_backend.resc_web_service.schema.scan import ScanCreate
from resc_backend.resc_web_service.schema.scan_type import ScanType


class TestScans(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[requires_auth] = requires_no_auth
        self.db_scans = []
        for i in range(1, 6):
            self.db_scans.append(
                DBscan(
                    repository_id=i,
                    scan_type="BASE",
                    last_scanned_commit="FAKE_HASH",
                    timestamp=datetime.now(UTC),
                    increment_number=0,
                    rule_pack=f"rule_pack_{i}",
                    is_latest=True,
                )
            )
            self.db_scans[i - 1].id_ = i

        self.db_repo = []
        for i in range(1, 6):
            self.db_repo.append(
                DBrepository(
                    project_key="project_key",
                    repository_id=str(i),
                    repository_name=f"repo_{i}",
                    repository_url=f"repo_url_{i}",
                    vcs_instance=1,
                    deleted_at=None,
                )
            )
            self.db_repo[i - 1].id_ = i

        self.db_repo[2].deleted_at = datetime.now(UTC)

        self.db_rules = []
        for i in range(1, 6):
            self.db_rules.append(
                DBrule(
                    rule_name=f"test{i}",
                    rule_pack=f"rule_pack_{i}",
                    description=f"descr{i}",
                )
            )
            self.db_rules[i - 1].id_ = i

        self.db_findings = []
        for i in range(1, 6):
            self.db_findings.append(
                DBfinding(
                    file_path=f"file_path_{i}",
                    line_number=i,
                    column_start=i,
                    column_end=i,
                    commit_id=f"commit_id_{i}",
                    commit_message=f"commit_message_{i}",
                    commit_timestamp=datetime.now(UTC),
                    author=f"author_{i}",
                    email=f"email_{i}",
                    rule_name=f"rule_{i}",
                    event_sent_on=datetime.now(UTC),
                    repository_id=1,
                )
            )
            self.db_findings[i - 1].id_ = i

        self.enriched_findings = []
        for i in range(1, 6):
            self.enriched_findings.append(
                FindingRead(
                    id_=i,
                    scan_ids=[i],
                    file_path=f"file_path_{i}",
                    line_number=i,
                    column_start=i,
                    column_end=i,
                    commit_id=f"commit_id_{i}",
                    commit_message=f"commit_message_{i}",
                    commit_timestamp=datetime.now(UTC),
                    author=f"author_{i}",
                    email=f"email_{i}",
                    repository_id=i,
                    rule_name=f"rule_{i}",
                    event_sent_on=datetime.now(UTC),
                )
            )
        self.repository_id = 1

    @staticmethod
    def create_json_body(scan):
        return {
            "timestamp": scan.timestamp.isoformat(),
            "scan_type": scan.scan_type,
            "last_scanned_commit": scan.last_scanned_commit,
            "repository_id": scan.repository_id,
            "increment_number": scan.increment_number,
            "rule_pack": scan.rule_pack,
        }

    @staticmethod
    def cast_db_scan_to_scan_create(scan):
        return ScanCreate(
            scan_type=scan.scan_type,
            last_scanned_commit=scan.last_scanned_commit,
            timestamp=scan.timestamp,
            repository_id=scan.repository_id,
            increment_number=scan.increment_number,
            rule_pack=scan.rule_pack,
        )

    @staticmethod
    def assert_scan(data, scan):
        assert data["id_"] == scan.id_
        assert data["repository_id"] == scan.repository_id
        assert datetime.fromisoformat(data["timestamp"]) == scan.timestamp

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    def test_get_scan_non_existing(self, get_scan):
        scan_id = 999
        get_scan.return_value = None
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/{scan_id}")
        assert response.status_code == 404, response.text
        data = response.json()
        assert data["detail"] == "Scan not found"
        get_scan.assert_called_once_with(ANY, scan_id=scan_id)

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    def test_get_scan(self, get_scan):
        db_scan = self.db_scans[0]
        get_scan.return_value = db_scan
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/{db_scan.id_}")
        assert response.status_code == 200, response.text
        self.assert_scan(response.json(), db_scan)
        get_scan.assert_called_once_with(ANY, scan_id=db_scan.id_)

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    @patch("resc_backend.resc_web_service.crud.scan.delete_scan")
    def test_delete_scan(self, delete_scan, get_scan):
        db_scan = self.db_scans[0]
        get_scan.return_value = db_scan
        response = self.client.delete(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/{db_scan.id_}")
        assert response.status_code == 200, response.text
        get_scan.assert_called_once_with(ANY, scan_id=db_scan.id_)
        delete_scan.assert_called_once_with(
            ANY,
            repository_id=db_scan.repository_id,
            scan_id=db_scan.id_,
            delete_related=True,
        )

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    @patch("resc_backend.resc_web_service.crud.scan.delete_scan")
    def test_delete_scans_non_existing(self, delete_scan, get_scan):
        db_scan_id = 999
        get_scan.return_value = None
        response = self.client.delete(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/{db_scan_id}")
        assert response.status_code == 404, response.text
        data = response.json()
        assert data["detail"] == "Scan not found"
        get_scan.assert_called_once_with(ANY, scan_id=db_scan_id)
        delete_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_post_scan(self, get_repository, create_scan):
        db_scan = self.db_scans[0]
        get_repository.return_value = self.db_repo[0]
        create_scan.return_value = db_scan
        response = self.client.post(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}",
            json=self.create_json_body(db_scan),
        )
        assert response.status_code == 201, response.text
        self.assert_scan(response.json(), db_scan)
        get_repository.assert_called_once_with(db_connection=ANY, repository_id=db_scan.repository_id)
        create_scan.assert_called_once_with(db_connection=ANY, scan=self.cast_db_scan_to_scan_create(db_scan))

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_post_scan_404_no_repo(self, get_repository, create_scan):
        db_scan = self.db_scans[0]
        get_repository.return_value = None
        response = self.client.post(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}",
            json=self.create_json_body(db_scan),
        )
        assert response.status_code == 404, response.text
        get_repository.assert_called_once_with(db_connection=ANY, repository_id=db_scan.repository_id)
        create_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    @patch("resc_backend.resc_web_service.crud.repository.undelete_repository")
    @patch("resc_backend.resc_web_service.crud.finding.get_finding_for_repository")
    @patch("resc_backend.resc_web_service.crud.audit.revert_last_audit")
    def test_post_scan_with_deleted_repository(
        self, revert_last_audit, get_finding_for_repository, undelete_repository, get_repository, create_scan
    ):
        db_scan = self.db_scans[0]
        get_repository.return_value = self.db_repo[2]
        create_scan.return_value = db_scan
        get_finding_for_repository.return_value = []
        response = self.client.post(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}",
            json=self.create_json_body(db_scan),
        )
        assert response.status_code == 201, response.text
        self.assert_scan(response.json(), db_scan)
        get_repository.assert_called_once_with(db_connection=ANY, repository_id=db_scan.repository_id)
        undelete_repository.assert_called_once_with(ANY, repository_ids=[self.db_repo[2].id_])
        get_finding_for_repository.assert_called_once_with(
            ANY, repository_ids=[self.db_repo[2].id_], status=FindingStatus.NOT_ACCESSIBLE, not_status=None
        )
        revert_last_audit.assert_called_once_with(ANY, finding_ids=[], status=FindingStatus.NOT_ACCESSIBLE)
        create_scan.assert_called_once_with(db_connection=ANY, scan=self.cast_db_scan_to_scan_create(db_scan))

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    @patch("resc_backend.resc_web_service.crud.scan.get_latest_scan_for_repository")
    @patch("resc_backend.resc_web_service.crud.repository.get_repository")
    def test_post_increment_scan(self, get_repository, get_latest_scan_for_repository, create_scan):
        db_scan = self.db_scans[0]
        get_repository.return_value = self.db_repo[0]
        db_scan.scan_type = ScanType.INCREMENTAL
        create_scan.return_value = db_scan
        get_latest_scan_for_repository.return_value = self.db_scans[1]
        response = self.client.post(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}",
            json=self.create_json_body(db_scan),
        )
        assert response.status_code == 201, response.text
        self.assert_scan(response.json(), db_scan)
        expected_scan = self.cast_db_scan_to_scan_create(db_scan)
        expected_scan.increment_number = 1
        create_scan.assert_called_once_with(db_connection=ANY, scan=expected_scan)

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    def test_post_scans_no_body(self, create_scan):
        response = self.client.post(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}",
        )
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["body"]
        assert data["detail"][0]["msg"] == "Field required"
        create_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    def test_post_scans_empty_body(self, create_scan):
        response = self.client.post(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}", json={})
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["body", "last_scanned_commit"]
        assert data["detail"][0]["msg"] == "Field required"
        assert data["detail"][1]["loc"] == ["body", "timestamp"]
        assert data["detail"][1]["msg"] == "Field required"
        assert data["detail"][2]["loc"] == ["body", "rule_pack"]
        assert data["detail"][2]["msg"] == "Field required"
        assert data["detail"][3]["loc"] == ["body", "repository_id"]
        assert data["detail"][3]["msg"] == "Field required"
        create_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.create_scan")
    def test_post_scans_invalid_timestamp(self, create_scan):
        response = self.client.post(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}",
            json={
                "repository_id": 1,
                "scan_type": "BASE",
                "last_scanned_commit": "dummy_commit",
                "timestamp": "invalid_time",
            },
        )
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["body", "timestamp"]
        assert data["detail"][0]["msg"] == "Input should be a valid datetime or date, invalid character in year"
        create_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    @patch("resc_backend.resc_web_service.crud.scan.update_scan")
    def test_put_scan(self, update_scan, get_scan):
        db_scan = self.db_scans[0]
        get_scan.return_value = db_scan
        update_scan.return_value = db_scan
        update_scan.return_value.timestamp = datetime.now(UTC)
        response = self.client.put(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/{db_scan.id_}",
            json=self.create_json_body(update_scan.return_value),
        )
        assert response.status_code == 200, response.text
        self.assert_scan(response.json(), update_scan.return_value)
        get_scan.assert_called_once_with(ANY, scan_id=db_scan.id_)
        update_scan.assert_called_once_with(
            db_connection=ANY,
            scan_id=db_scan.id_,
            scan=self.cast_db_scan_to_scan_create(update_scan.return_value),
        )

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    @patch("resc_backend.resc_web_service.crud.scan.update_scan")
    def test_put_scans_non_existing(self, update_scan, get_scan):
        db_scan_id = 999
        get_scan.return_value = None
        response = self.client.put(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/{db_scan_id}",
            json={
                "scan_type": "BASE",
                "last_scanned_commit": "dummy_commit",
                "timestamp": "2021-09-12T17:38:28.501000",
                "vcs_provider": "dummy_vcs_provider",
                "repository_id": 999,
                "rule_pack": "1.5",
            },
        )
        assert response.status_code == 404, response.text
        data = response.json()
        assert data["detail"] == "Scan not found"
        get_scan.assert_called_once_with(ANY, scan_id=db_scan_id)
        update_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.get_scan")
    @patch("resc_backend.resc_web_service.crud.scan.update_scan")
    def test_put_scans_empty_body(self, update_scan, get_scan):
        response = self.client.put(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/9999999999", json={})
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["body", "last_scanned_commit"]
        assert data["detail"][0]["msg"] == "Field required"
        assert data["detail"][1]["loc"] == ["body", "timestamp"]
        assert data["detail"][1]["msg"] == "Field required"
        assert data["detail"][2]["loc"] == ["body", "rule_pack"]
        assert data["detail"][2]["msg"] == "Field required"
        assert data["detail"][3]["loc"] == ["body", "repository_id"]
        assert data["detail"][3]["msg"] == "Field required"
        update_scan.assert_not_called()
        get_scan.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.get_scans_count")
    @patch("resc_backend.resc_web_service.crud.scan.get_scans")
    def test_get_multiple_scans(self, get_scans, get_scans_count):
        get_scans.return_value = self.db_scans[:2]
        get_scans_count.return_value = len(self.db_scans[:2])
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}", params={"skip": 0, "limit": 5})
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["data"]) == 2
        self.assert_scan(data["data"][0], self.db_scans[0])
        self.assert_scan(data["data"][1], self.db_scans[1])
        assert data["total"] == 2
        assert data["limit"] == 5
        assert data["skip"] == 0

    @patch("resc_backend.resc_web_service.crud.scan.get_scans")
    def test_get_multiple_scans_with_negative_skip(self, get_scans):
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}", params={"skip": -1, "limit": 5})
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["query", "skip"]
        assert data["detail"][0]["msg"] == "Input should be greater than or equal to 0"
        get_scans.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.scan.get_scans")
    def test_get_multiple_scans_with_negative_limit(self, get_scans):
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}", params={"skip": 0, "limit": -1})
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["query", "limit"]
        assert data["detail"][0]["msg"] == "Input should be greater than or equal to 1"
        get_scans.assert_not_called()

    @patch("resc_backend.resc_web_service.crud.finding.get_scans_findings")
    @patch("resc_backend.resc_web_service.crud.finding.get_total_findings_count")
    def test_get_scan_findings(self, get_total_findings_count, get_scan_findings):
        get_scan_findings.return_value = self.enriched_findings
        get_total_findings_count.return_value = 5
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/1{RWS_ROUTE_FINDINGS}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data"][0]["id_"] == self.enriched_findings[0].id_
        assert data["data"][0]["scan_ids"] == self.enriched_findings[0].scan_ids
        assert data["data"][4]["id_"] == self.enriched_findings[4].id_
        assert data["data"][4]["scan_ids"] == self.enriched_findings[4].scan_ids
        assert data["total"] == 5
        assert data["limit"] == 100
        assert data["skip"] == 0

    @patch("resc_backend.resc_web_service.crud.finding.get_scans_findings")
    @patch("resc_backend.resc_web_service.crud.finding.get_total_findings_count")
    def test_get_scan_findings_non_existing(self, get_total_findings_count, get_scan_findings):
        get_scan_findings.return_value = []
        get_total_findings_count.return_value = 0
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/9999{RWS_ROUTE_FINDINGS}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["skip"] == 0

    def test_get_scan_findings_invalid_id(self):
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}/invalid{RWS_ROUTE_FINDINGS}")
        assert response.status_code == 422, response.text
        data = response.json()
        assert data["detail"][0]["loc"] == ["path", "scan_id"]
        assert data["detail"][0]["msg"] == "Input should be a valid integer, unable to parse string as an integer"
        assert data["detail"][0]["type"] == "int_parsing"

    @patch("resc_backend.resc_web_service.crud.finding.get_distinct_rules_from_scans")
    def test_get_distinct_rules_from_scans(self, get_distinct_rules_from_scans):
        get_distinct_rules_from_scans.return_value = self.db_rules
        response = self.client.get(
            f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}{RWS_ROUTE_DETECTED_RULES}/?scan_id=1&scan_id=2"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == len(self.db_rules)
        assert data[0] == self.db_rules[0].rule_name
        assert data[4] == self.db_rules[4].rule_name

    @patch("resc_backend.resc_web_service.crud.finding.get_scans_findings")
    @patch("resc_backend.resc_web_service.crud.finding.get_total_findings_count")
    def test_get_scans_findings(self, get_total_findings_count, get_scans_findings):
        get_scans_findings.return_value = self.enriched_findings
        get_total_findings_count.return_value = 5
        response = self.client.get(
            f"{RWS_VERSION_PREFIX}"
            f"{RWS_ROUTE_SCANS}{RWS_ROUTE_FINDINGS}/"
            f"?scan_id={self.enriched_findings[0].id_}&scan_id={self.enriched_findings[1].id_}"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data"][0]["id_"] == self.enriched_findings[0].id_
        assert data["data"][0]["scan_ids"] == self.enriched_findings[0].scan_ids
        assert data["data"][4]["id_"] == self.enriched_findings[4].id_
        assert data["data"][4]["scan_ids"] == self.enriched_findings[4].scan_ids
        assert data["total"] == 5
        assert data["limit"] == 100
        assert data["skip"] == 0

    @patch("resc_backend.resc_web_service.crud.finding.get_scans_findings")
    @patch("resc_backend.resc_web_service.crud.finding.get_total_findings_count")
    def test_get_scans_findings_non_existing(self, get_total_findings_count, get_scans_findings):
        get_scans_findings.return_value = []
        get_total_findings_count.return_value = 0
        response = self.client.get(f"{RWS_VERSION_PREFIX}{RWS_ROUTE_SCANS}{RWS_ROUTE_FINDINGS}/")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["skip"] == 0
