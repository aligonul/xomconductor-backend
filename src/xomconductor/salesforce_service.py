"""Salesforce integration for case management."""

import os
from dataclasses import dataclass
from typing import Optional

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed


@dataclass
class CaseDetails:
    id: str
    case_number: str
    subject: str
    description: str
    status: str
    priority: str
    contact_name: str
    contact_email: str
    account_name: str
    owner_name: str
    created_date: str
    last_modified_date: str

    @classmethod
    def from_sf_record(cls, record: dict) -> "CaseDetails":
        return cls(
            id=record["Id"],
            case_number=record["CaseNumber"],
            subject=record.get("Subject") or "",
            description=record.get("Description") or "",
            status=record.get("Status") or "",
            priority=record.get("Priority") or "",
            contact_name=record.get("Contact", {}).get("Name") if record.get("Contact") else "",
            contact_email=record.get("Contact", {}).get("Email") if record.get("Contact") else "",
            account_name=record.get("Account", {}).get("Name") if record.get("Account") else "",
            owner_name=record.get("Owner", {}).get("Name") if record.get("Owner") else "",
            created_date=record.get("CreatedDate") or "",
            last_modified_date=record.get("LastModifiedDate") or "",
        )


class SalesforceClient:
    """Salesforce API client wrapper."""

    def __init__(self):
        self._sf: Optional[Salesforce] = None

    def connect(self) -> bool:
        """Establish connection to Salesforce using available auth method."""
        # Try OAuth first (for SSO orgs like Xometry with Okta)
        if os.getenv("SF_ACCESS_TOKEN") and os.getenv("SF_INSTANCE_URL"):
            return self._connect_oauth()

        # Fall back to username/password (for non-SSO orgs)
        if os.getenv("SF_USERNAME") and os.getenv("SF_PASSWORD"):
            return self._connect_password()

        raise ConnectionError("No Salesforce credentials configured")

    def _connect_oauth(self) -> bool:
        """Connect using OAuth access token."""
        try:
            self._sf = Salesforce(
                instance_url=os.environ["SF_INSTANCE_URL"],
                session_id=os.environ["SF_ACCESS_TOKEN"],
            )
            return True
        except Exception as e:
            raise ConnectionError(f"Salesforce OAuth connection failed: {e}")

    def _connect_password(self) -> bool:
        """Connect using username/password."""
        try:
            self._sf = Salesforce(
                username=os.environ["SF_USERNAME"],
                password=os.environ["SF_PASSWORD"],
                security_token=os.environ.get("SF_SECURITY_TOKEN", ""),
                domain=os.getenv("SF_DOMAIN", "login"),
            )
            return True
        except SalesforceAuthenticationFailed as e:
            raise ConnectionError(f"Salesforce authentication failed: {e}")

    @property
    def sf(self) -> Salesforce:
        if not self._sf:
            self.connect()
        return self._sf

    def get_case_by_number(self, case_number: str) -> Optional[CaseDetails]:
        """Fetch case details by case number."""
        clean_number = case_number.replace("'", "").replace(";", "").strip()
        query = f"""
            SELECT Id, CaseNumber, Subject, Description, Status, Priority,
                   Contact.Name, Contact.Email,
                   Account.Name,
                   Owner.Name,
                   CreatedDate, LastModifiedDate
            FROM Case
            WHERE CaseNumber = '{clean_number}'
            LIMIT 1
        """
        result = self.sf.query(query)

        if result["totalSize"] == 0:
            return None

        return CaseDetails.from_sf_record(result["records"][0])

    def get_case_by_id(self, case_id: str) -> Optional[CaseDetails]:
        """Fetch case details by Salesforce ID."""
        clean_id = case_id.replace("'", "").replace(";", "").strip()
        query = f"""
            SELECT Id, CaseNumber, Subject, Description, Status, Priority,
                   Contact.Name, Contact.Email,
                   Account.Name,
                   Owner.Name,
                   CreatedDate, LastModifiedDate
            FROM Case
            WHERE Id = '{clean_id}'
            LIMIT 1
        """
        result = self.sf.query(query)

        if result["totalSize"] == 0:
            return None

        return CaseDetails.from_sf_record(result["records"][0])

    def search_cases(self, search_term: str, limit: int = 10) -> list[CaseDetails]:
        """Search cases by subject or case number."""
        clean_term = search_term.replace("'", "").replace(";", "").strip()
        query = f"""
            SELECT Id, CaseNumber, Subject, Description, Status, Priority,
                   Contact.Name, Contact.Email,
                   Account.Name,
                   Owner.Name,
                   CreatedDate, LastModifiedDate
            FROM Case
            WHERE CaseNumber LIKE '%{clean_term}%'
               OR Subject LIKE '%{clean_term}%'
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """
        result = self.sf.query(query)
        return [CaseDetails.from_sf_record(r) for r in result["records"]]

    def add_case_comment(self, case_id: str, comment_body: str, is_public: bool = False) -> str:
        """Add a comment to a case."""
        result = self.sf.CaseComment.create({
            "ParentId": case_id,
            "CommentBody": comment_body,
            "IsPublished": is_public,
        })
        return result["id"]

    def send_email_from_case(
        self,
        case_id: str,
        to_address: str,
        subject: str,
        body: str,
    ) -> str:
        """Send an email associated with a case using Salesforce EmailMessage."""
        result = self.sf.EmailMessage.create({
            "ParentId": case_id,
            "ToAddress": to_address,
            "Subject": subject,
            "TextBody": body,
            "Status": "3",  # 3 = Sent
        })
        return result["id"]

    def create_email_draft(
        self,
        case_id: str,
        to_address: str,
        subject: str,
        body: str,
    ) -> str:
        """Create an email draft associated with a case."""
        result = self.sf.EmailMessage.create({
            "ParentId": case_id,
            "ToAddress": to_address,
            "Subject": subject,
            "TextBody": body,
            "Status": "0",  # 0 = Draft
        })
        return result["id"]


# Singleton instance
_client: Optional[SalesforceClient] = None


def get_client() -> SalesforceClient:
    """Get or create the Salesforce client singleton."""
    global _client
    if _client is None:
        _client = SalesforceClient()
    return _client


def is_configured() -> bool:
    """Check if Salesforce credentials are configured (either OAuth or password)."""
    oauth_configured = os.getenv("SF_ACCESS_TOKEN") and os.getenv("SF_INSTANCE_URL")
    password_configured = os.getenv("SF_USERNAME") and os.getenv("SF_PASSWORD")
    return bool(oauth_configured or password_configured)


def get_auth_method() -> str:
    """Return which auth method is configured."""
    if os.getenv("SF_ACCESS_TOKEN") and os.getenv("SF_INSTANCE_URL"):
        return "oauth"
    if os.getenv("SF_USERNAME") and os.getenv("SF_PASSWORD"):
        return "password"
    return "none"
