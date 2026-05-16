import requests
from config import SF_CLIENT_ID, SF_CLIENT_SECRET, SF_REFRESH_TOKEN, SF_INSTANCE_URL


class SalesforceClient:
    def __init__(self):
        self.instance_url = SF_INSTANCE_URL
        self.access_token = None

    def refresh_access_token(self):
        """Refresh the Salesforce access token using the refresh token."""
        token_url = "https://login.salesforce.com/services/oauth2/token"

        response = requests.post(token_url, data={
            "grant_type": "refresh_token",
            "client_id": SF_CLIENT_ID,
            "client_secret": SF_CLIENT_SECRET,
            "refresh_token": SF_REFRESH_TOKEN
        })

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            if "instance_url" in data:
                self.instance_url = data["instance_url"]
            return True
        else:
            raise Exception(f"Failed to refresh token: {response.text}")

    def ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if not self.access_token:
            self.refresh_access_token()

    def send_email(self, case_id: str, to_address: str, subject: str, body: str,
                   cc_addresses: list = None, from_address: str = None) -> dict:
        """
        Send an email via Salesforce, linked to a Case.

        Args:
            case_id: Salesforce Case ID
            to_address: Recipient email address
            subject: Email subject
            body: Email body (HTML supported)
            cc_addresses: Optional list of CC addresses
            from_address: Optional org-wide email address ID

        Returns:
            Dictionary with send result
        """
        self.ensure_authenticated()

        email_message = {
            "inputs": [{
                "emailAddresses": to_address,
                "emailSubject": subject,
                "emailBody": body,
                "senderType": "CurrentUser",
                "relatedToId": case_id
            }]
        }

        if cc_addresses:
            email_message["inputs"][0]["emailAddressesCC"] = ",".join(cc_addresses)

        if from_address:
            email_message["inputs"][0]["senderAddress"] = from_address
            email_message["inputs"][0]["senderType"] = "OrgWideEmailAddress"

        url = f"{self.instance_url}/services/data/v59.0/actions/standard/emailSimple"

        response = requests.post(
            url,
            json=email_message,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 200:
            return {"success": True, "response": response.json()}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}

    def get_case_details(self, case_id: str) -> dict:
        """Fetch case details from Salesforce."""
        self.ensure_authenticated()

        url = f"{self.instance_url}/services/data/v59.0/sobjects/Case/{case_id}"

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get case: {response.text}")

    def get_case_contact_email(self, case_id: str) -> str:
        """Get the contact email for a case."""
        case = self.get_case_details(case_id)
        contact_id = case.get("ContactId")

        if not contact_id:
            return case.get("SuppliedEmail", "")

        url = f"{self.instance_url}/services/data/v59.0/sobjects/Contact/{contact_id}"

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 200:
            return response.json().get("Email", "")
        return ""


sf_client = SalesforceClient()
