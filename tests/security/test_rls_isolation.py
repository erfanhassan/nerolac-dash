"""Security Integration Test Suite: Microsoft Entra ID SSO & PostgreSQL Row-Level Security (RLS).

Verifies:
1. Microsoft Entra ID (Azure AD) OIDC token issuance, signature checks, and claim extraction:
   (user_id, user_role, depot_id).
2. JWT Validation Middleware in auth_middleware.py extracting claims on incoming requests.
3. PostgreSQL RLS session variables:
   - SET LOCAL app.current_depot_id = 'CTG';
   - SET LOCAL app.current_user_role = 'DEPOT_MANAGER';
4. Strict regional depot isolation enforcing RLS policies across 4 operational tables:
   - financial_actuals
   - historical_sales
   - employee_kpi_scores
   - whatsapp_parsed_sales
5. Physical blocking of cross-depot queries when executing with a Chittagong Manager token.
6. Executive corporate role bypass (SUPER_ADMIN, FINANCE_MANAGER, SALES_DIRECTOR).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from src.backend.auth.sso_handler import (
    AuthenticationError,
    TokenExpiredError,
    UserClaims,
    create_test_token,
    get_sso_handler,
)
from src.backend.database.rls_manager import setup_row_level_security, verify_rls_status
from src.backend.database.session_router import (
    get_read_session,
    get_routing_manager,
    rls_context,
)
from src.backend.main import app

# Unique keys for test fixtures to ensure idempotent test isolation
TEST_ACCOUNT_ID = "ACC_RLS_10000"
TEST_SKU_ID = "SKU_RLS_ISOLATION"
TEST_EMP_CTG = "EMP_RLS_CTG_01"
TEST_EMP_DHK = "EMP_RLS_DHK_01"
TEST_DLR_CTG = "DLR_RLS_CTG_01"
TEST_DLR_DHK = "DLR_RLS_DHK_01"
TEST_RAW_MSG_CTG = 98101
TEST_RAW_MSG_DHK = 98102


@pytest.fixture(scope="module", autouse=True)
async def setup_rls_and_test_fixtures() -> AsyncIterator[None]:
    """Ensure RLS policies are enabled and seed test master entities."""
    # 1. Enforce RLS policies
    await setup_row_level_security()

    # 2. Seed Master data under Primary write engine (superuser bypass)
    router = get_routing_manager()
    async with router.primary_engine.begin() as conn:
        # Chart of Accounts
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.chart_of_accounts
                    (account_id, account_code, account_name, account_type)
                VALUES
                    (:acc_id, '10000', 'Gross Sales Revenue', 'REVENUE')
                ON CONFLICT (account_id) DO NOTHING;
                """
            ),
            {"acc_id": TEST_ACCOUNT_ID},
        )

        # SKU
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.skus
                    (sku_id, sku_code, sku_name, category, unit_price)
                VALUES
                    (:sku_id, :sku_id, 'Weather Defense Exterior 20L', 'EXTERIOR', 4850.00)
                ON CONFLICT (sku_id) DO NOTHING;
                """
            ),
            {"sku_id": TEST_SKU_ID},
        )

        # Employees
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.employees
                    (employee_id, employee_code, full_name, department, designation, depot_id)
                VALUES
                    (:emp_ctg, :emp_ctg, 'Chittagong Field Officer', 'SALES', 'TSO', 'CTG'),
                    (:emp_dhk, :emp_dhk, 'Dhaka Field Officer', 'SALES', 'TSO', 'DHK')
                ON CONFLICT (employee_id) DO NOTHING;
                """
            ),
            {"emp_ctg": TEST_EMP_CTG, "emp_dhk": TEST_EMP_DHK},
        )

        # Dealers
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.dealers
                    (dealer_id, dealer_code, trade_name, depot_id)
                VALUES
                    (:dlr_ctg, :dlr_ctg, 'Agrabad Paints CTG', 'CTG'),
                    (:dlr_dhk, :dlr_dhk, 'Mirpur Hardware DHK', 'DHK')
                ON CONFLICT (dealer_id) DO NOTHING;
                """
            ),
            {"dlr_ctg": TEST_DLR_CTG, "dlr_dhk": TEST_DLR_DHK},
        )

        # WhatsApp Raw Messages
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.whatsapp_raw_messages
                    (raw_id, waba_message_id, sender_phone, raw_payload, status)
                VALUES
                    (
                        :msg_ctg, 'wamid_rls_ctg_test', '+8801811111111',
                        '{"text": "CTG sale"}', 'PARSED'
                    ),
                    (
                        :msg_dhk, 'wamid_rls_dhk_test', '+8801711111111',
                        '{"text": "DHK sale"}', 'PARSED'
                    )
                ON CONFLICT (raw_id) DO NOTHING;
                """
            ),
            {"msg_ctg": TEST_RAW_MSG_CTG, "msg_dhk": TEST_RAW_MSG_DHK},
        )

        # Insert Transactional Records into the 4 isolated tables
        # 1. Financial Actuals
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.financial_actuals
                    (depot_id, account_id, amount, fiscal_year, fiscal_month, transaction_date)
                VALUES
                    ('CTG', :acc, 650000.00, 2026, 1, '2026-04-15'),
                    ('DHK', :acc, 1250000.00, 2026, 1, '2026-04-15');
                """
            ),
            {"acc": TEST_ACCOUNT_ID},
        )

        # 2. Historical Sales
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.historical_sales
                    (depot_id, sku_id, dealer_id, quantity_liters, net_revenue, sales_date)
                VALUES
                    ('CTG', :sku, :dlr_ctg, 1500.0, 650000.00, '2026-04-10'),
                    ('DHK', :sku, :dlr_dhk, 3000.0, 1250000.00, '2026-04-10');
                """
            ),
            {"sku": TEST_SKU_ID, "dlr_ctg": TEST_DLR_CTG, "dlr_dhk": TEST_DLR_DHK},
        )

        # 3. Employee KPI Scores
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.employee_kpi_scores
                    (employee_id, assessment_period, target_score, achieved_score, weightage)
                VALUES
                    (:emp_ctg, 'FY2026-Q1', 90.0, 94.5, 1.0),
                    (:emp_dhk, 'FY2026-Q1', 90.0, 87.0, 1.0);
                """
            ),
            {"emp_ctg": TEST_EMP_CTG, "emp_dhk": TEST_EMP_DHK},
        )

        # 4. WhatsApp Parsed Sales
        await conn.execute(
            text(
                """
                INSERT INTO nerolac_ops.whatsapp_parsed_sales
                    (raw_message_id, dealer_id, sku_id, parsed_quantity, parsed_price, status)
                VALUES
                    (:msg_ctg, :dlr_ctg, :sku, 1500.0, 650000.00, 'CONFIRMED'),
                    (:msg_dhk, :dlr_dhk, :sku, 3000.0, 1250000.00, 'CONFIRMED');
                """
            ),
            {
                "msg_ctg": TEST_RAW_MSG_CTG,
                "msg_dhk": TEST_RAW_MSG_DHK,
                "dlr_ctg": TEST_DLR_CTG,
                "dlr_dhk": TEST_DLR_DHK,
                "sku": TEST_SKU_ID,
            },
        )

    yield

    # Clean up test transactional rows
    async with router.primary_engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM nerolac_ops.financial_actuals WHERE account_id = :acc;"),
            {"acc": TEST_ACCOUNT_ID},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.historical_sales WHERE sku_id = :sku;"),
            {"sku": TEST_SKU_ID},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.employee_kpi_scores WHERE employee_id IN (:e1, :e2);"),
            {"e1": TEST_EMP_CTG, "e2": TEST_EMP_DHK},
        )
        await conn.execute(
            text(
                "DELETE FROM nerolac_ops.whatsapp_parsed_sales WHERE raw_message_id IN (:m1, :m2);"
            ),
            {"m1": TEST_RAW_MSG_CTG, "m2": TEST_RAW_MSG_DHK},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.dealers WHERE dealer_id IN (:d1, :d2);"),
            {"d1": TEST_DLR_CTG, "d2": TEST_DLR_DHK},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.employees WHERE employee_id IN (:e1, :e2);"),
            {"e1": TEST_EMP_CTG, "e2": TEST_EMP_DHK},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.whatsapp_raw_messages WHERE raw_id IN (:m1, :m2);"),
            {"m1": TEST_RAW_MSG_CTG, "m2": TEST_RAW_MSG_DHK},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.skus WHERE sku_id = :sku;"),
            {"sku": TEST_SKU_ID},
        )
        await conn.execute(
            text("DELETE FROM nerolac_ops.chart_of_accounts WHERE account_id = :acc;"),
            {"acc": TEST_ACCOUNT_ID},
        )


class TestMicrosoftEntraIDSSO:
    """Verifies Requirement 1: Microsoft Entra ID OIDC / OAuth2 token exchange and validation."""

    def test_entra_id_token_issuance_and_claim_extraction(self) -> None:
        """Verify JWT minting, signature check, and canonical claim extraction."""
        handler = get_sso_handler()

        # Generate a signed Chittagong Manager token
        ctg_token = handler.create_test_token(
            user_id="USR_CTG_MGR_01",
            user_role="DEPOT_MANAGER",
            depot_id="CTG",
            email="ctg.manager@nerolacbd.com",
            full_name="Chittagong Depot Manager",
        )
        assert ctg_token is not None
        assert len(ctg_token.split(".")) == 3

        # Decode and validate claims
        claims: UserClaims = handler.decode_and_validate_token(ctg_token)
        assert claims.user_id == "USR_CTG_MGR_01"
        assert claims.user_role == "DEPOT_MANAGER"
        assert claims.depot_id == "CTG"
        assert claims.email == "ctg.manager@nerolacbd.com"
        assert claims.is_executive_role() is False

    def test_entra_id_token_tampered_signature_rejected(self) -> None:
        """Assert that tampering with token payload invalidates HMAC signature."""
        handler = get_sso_handler()
        token = handler.create_test_token(user_id="USR_CTG_01", depot_id="CTG")
        header, payload, sig = token.split(".")

        # Tamper payload
        tampered_token = f"{header}.eyJ1c2VyX2lkIjoiSEFDS0VEIn0.{sig}"
        with pytest.raises(AuthenticationError):
            handler.decode_and_validate_token(tampered_token)

    def test_entra_id_expired_token_rejected(self) -> None:
        """Assert that expired tokens raise TokenExpiredError."""
        handler = get_sso_handler()
        expired_token = handler.create_test_token(
            user_id="USR_EXPIRED",
            expires_in_seconds=-120,  # Expired 2 minutes ago
        )
        with pytest.raises(TokenExpiredError):
            handler.decode_and_validate_token(expired_token, leeway_seconds=10)

    def test_entra_id_authorization_url_generation(self) -> None:
        """Verify Microsoft Entra ID authorization login URL generation."""
        handler = get_sso_handler()
        url = handler.get_authorization_url(
            redirect_uri="https://nerolacbd.com/api/v1/auth/callback",
            state="state_xyz",
        )
        assert "login.microsoftonline.com" in url
        assert "response_type=code" in url
        assert "state=state_xyz" in url
        assert "client_id=" in url


class TestAuthMiddleware:
    """Verifies Requirement 2: JWT validation middleware extracting claims on API requests."""

    @pytest.mark.asyncio
    async def test_auth_middleware_extracts_claims_from_bearer_token(self) -> None:
        """Assert /api/v1/auth/me extracts user_id, user_role, and depot_id into request state."""
        ctg_token = create_test_token(
            user_id="USR_CHITTAGONG_01",
            user_role="DEPOT_MANAGER",
            depot_id="CTG",
            email="chittagong@nerolacbd.com",
            full_name="Agrabad Depot Lead",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {ctg_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "USR_CHITTAGONG_01"
            assert data["user_role"] == "DEPOT_MANAGER"
            assert data["depot_id"] == "CTG"
            assert data["email"] == "chittagong@nerolacbd.com"
            assert data["is_executive"] is False

    @pytest.mark.asyncio
    async def test_auth_middleware_rejects_missing_or_invalid_bearer_token(self) -> None:
        """Assert 401 Unauthorized when token is omitted or invalid on protected endpoints."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Missing token
            res_no_auth = await client.get("/api/v1/auth/me")
            assert res_no_auth.status_code == 401

            # Invalid Bearer token
            res_bad_token = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid.malformed.jwt.token"},
            )
            assert res_bad_token.status_code == 401


class TestPostgreSQLRowLevelSecurityIsolation:
    """Verifies Requirements 3, 4: PostgreSQL RLS regional depot isolation."""

    @pytest.mark.asyncio
    async def test_rls_policies_active_on_all_four_tables(self) -> None:
        """Verify RLS is active and forced on all four operational tables."""
        status = await verify_rls_status()
        assert status["all_secure"] is True
        for tbl in [
            "financial_actuals",
            "historical_sales",
            "employee_kpi_scores",
            "whatsapp_parsed_sales",
        ]:
            info = status["tables"][tbl]
            assert info["rls_enabled"] is True
            assert info["rls_forced"] is True
            assert info["policy_count"] >= 1

    @pytest.mark.asyncio
    async def test_financial_actuals_chittagong_isolation_and_cross_depot_blocking(self) -> None:
        """Assert CTG token isolates financial_actuals and blocks Dhaka access."""
        router = get_routing_manager()

        async with router.primary_engine.connect() as conn:
            # Start explicit transaction to ensure SET LOCAL scoping
            trans = await conn.begin()
            try:
                # 1. Apply RLS session variables
                await conn.execute(text("SET LOCAL ROLE nerolac_rls_user;"))
                await conn.execute(text("SET LOCAL app.current_depot_id = 'CTG';"))
                await conn.execute(text("SET LOCAL app.current_user_role = 'DEPOT_MANAGER';"))

                # 2. Unfiltered query: RLS must hide Dhaka record and only yield Chittagong
                res_all = await conn.execute(
                    text(
                        """
                        SELECT depot_id, amount
                        FROM nerolac_ops.financial_actuals
                        WHERE account_id = :acc;
                        """
                    ),
                    {"acc": TEST_ACCOUNT_ID},
                )
                rows = res_all.fetchall()
                assert len(rows) == 1, f"Expected 1 CTG row, got {len(rows)}"
                assert rows[0][0] == "CTG"
                assert float(rows[0][1]) == 650000.00

                # 3. Explicit cross-depot query attempt: Querying DHK must return 0 rows
                res_cross = await conn.execute(
                    text(
                        """
                        SELECT depot_id, amount
                        FROM nerolac_ops.financial_actuals
                        WHERE depot_id = 'DHK' AND account_id = :acc;
                        """
                    ),
                    {"acc": TEST_ACCOUNT_ID},
                )
                cross_rows = res_cross.fetchall()
                assert len(cross_rows) == 0, (
                    f"PostgreSQL RLS breach! CTG manager queried Dhaka rows: {cross_rows}"
                )

                # 4. Attempt querying another depot (DEPOT_01, DEPOT_03): must return 0 rows
                res_sylhet = await conn.execute(
                    text(
                        """
                        SELECT depot_id, amount
                        FROM nerolac_ops.financial_actuals
                        WHERE depot_id = 'DEPOT_03' AND account_id = :acc;
                        """
                    ),
                    {"acc": TEST_ACCOUNT_ID},
                )
                assert len(res_sylhet.fetchall()) == 0

            finally:
                await trans.rollback()

    @pytest.mark.asyncio
    async def test_historical_sales_chittagong_isolation_and_cross_depot_blocking(self) -> None:
        """Assert CTG Manager token isolates historical_sales and physically blocks Dhaka sales."""
        router = get_routing_manager()

        async with router.primary_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(text("SET LOCAL ROLE nerolac_rls_user;"))
                await conn.execute(text("SET LOCAL app.current_depot_id = 'CTG';"))
                await conn.execute(text("SET LOCAL app.current_user_role = 'DEPOT_MANAGER';"))

                # Query sales: CTG visible, Dhaka blocked
                res = await conn.execute(
                    text(
                        """
                        SELECT depot_id, quantity_liters, net_revenue
                        FROM nerolac_ops.historical_sales
                        WHERE sku_id = :sku;
                        """
                    ),
                    {"sku": TEST_SKU_ID},
                )
                rows = res.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == "CTG"
                assert float(rows[0][1]) == 1500.0

                # Cross-depot query attempt
                res_cross = await conn.execute(
                    text(
                        """
                        SELECT * FROM nerolac_ops.historical_sales
                        WHERE depot_id = 'DHK' AND sku_id = :sku;
                        """
                    ),
                    {"sku": TEST_SKU_ID},
                )
                assert len(res_cross.fetchall()) == 0, (
                    "RLS failed to block cross-depot sales query!"
                )

            finally:
                await trans.rollback()

    @pytest.mark.asyncio
    async def test_employee_kpi_scores_chittagong_isolation_and_cross_depot_blocking(self) -> None:
        """Assert CTG Manager can only view CTG employee KPIs, blocking Dhaka employees."""
        router = get_routing_manager()

        async with router.primary_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(text("SET LOCAL ROLE nerolac_rls_user;"))
                await conn.execute(text("SET LOCAL app.current_depot_id = 'CTG';"))
                await conn.execute(text("SET LOCAL app.current_user_role = 'DEPOT_MANAGER';"))

                res = await conn.execute(
                    text(
                        """
                        SELECT employee_id, achieved_score
                        FROM nerolac_ops.employee_kpi_scores
                        WHERE employee_id IN (:e1, :e2);
                        """
                    ),
                    {"e1": TEST_EMP_CTG, "e2": TEST_EMP_DHK},
                )
                rows = res.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == TEST_EMP_CTG
                assert float(rows[0][1]) == 94.5

                # Cross-depot query attempt for Dhaka employee
                res_cross = await conn.execute(
                    text(
                        """
                        SELECT * FROM nerolac_ops.employee_kpi_scores
                        WHERE employee_id = :e_dhk;
                        """
                    ),
                    {"e_dhk": TEST_EMP_DHK},
                )
                assert len(res_cross.fetchall()) == 0, (
                    "RLS failed to block cross-depot employee KPI score!"
                )

            finally:
                await trans.rollback()

    @pytest.mark.asyncio
    async def test_whatsapp_parsed_sales_chittagong_isolation_and_cross_depot_blocking(
        self,
    ) -> None:
        """Assert CTG Manager only views sales parsed for CTG dealers, blocking Dhaka dealers."""
        router = get_routing_manager()

        async with router.primary_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(text("SET LOCAL ROLE nerolac_rls_user;"))
                await conn.execute(text("SET LOCAL app.current_depot_id = 'CTG';"))
                await conn.execute(text("SET LOCAL app.current_user_role = 'DEPOT_MANAGER';"))

                res = await conn.execute(
                    text(
                        """
                        SELECT dealer_id, parsed_quantity, parsed_price
                        FROM nerolac_ops.whatsapp_parsed_sales
                        WHERE raw_message_id IN (:m1, :m2);
                        """
                    ),
                    {"m1": TEST_RAW_MSG_CTG, "m2": TEST_RAW_MSG_DHK},
                )
                rows = res.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == TEST_DLR_CTG
                assert float(rows[0][1]) == 1500.0

                # Cross-depot query attempt for Dhaka dealer
                res_cross = await conn.execute(
                    text(
                        """
                        SELECT * FROM nerolac_ops.whatsapp_parsed_sales
                        WHERE dealer_id = :d_dhk;
                        """
                    ),
                    {"d_dhk": TEST_DLR_DHK},
                )
                assert len(res_cross.fetchall()) == 0, (
                    "RLS failed to block cross-depot WhatsApp parsed sales!"
                )

            finally:
                await trans.rollback()

    @pytest.mark.asyncio
    async def test_executive_corporate_role_bypass(self) -> None:
        """Assert that executive roles bypass depot isolation to access all records."""
        router = get_routing_manager()

        for exec_role in ["SUPER_ADMIN", "SALES_DIRECTOR", "FINANCE_MANAGER"]:
            async with router.primary_engine.connect() as conn:
                trans = await conn.begin()
                try:
                    await conn.execute(text("SET LOCAL ROLE nerolac_rls_user;"))
                    await conn.execute(text(f"SET LOCAL app.current_user_role = '{exec_role}';"))

                    # Query financial actuals: Should see both CTG and DHK
                    res = await conn.execute(
                        text(
                            """
                            SELECT depot_id FROM nerolac_ops.financial_actuals
                            WHERE account_id = :acc
                            ORDER BY depot_id;
                            """
                        ),
                        {"acc": TEST_ACCOUNT_ID},
                    )
                    depots = [r[0] for r in res.fetchall()]
                    assert "CTG" in depots
                    assert "DHK" in depots
                    assert len(depots) >= 2, f"Executive role {exec_role} failed to view all depots"

                finally:
                    await trans.rollback()

    @pytest.mark.asyncio
    async def test_session_router_rls_context_manager(self) -> None:
        """Assert get_read_session with rls_context automatically applies session variables."""
        async with rls_context(depot_id="CTG", user_role="DEPOT_MANAGER"):
            async with get_read_session() as session:
                res = await session.execute(
                    text(
                        """
                        SELECT depot_id FROM nerolac_ops.financial_actuals
                        WHERE account_id = :acc;
                        """
                    ),
                    {"acc": TEST_ACCOUNT_ID},
                )
                rows = res.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == "CTG"

    @pytest.mark.asyncio
    async def test_api_endpoint_with_chittagong_manager_token(self) -> None:
        """Assert API request with CTG Manager Bearer token physically isolates database actuals."""
        ctg_token = create_test_token(
            user_id="USR_CTG_API_01",
            user_role="DEPOT_MANAGER",
            depot_id="CTG",
        )
        admin_token = create_test_token(
            user_id="USR_ADMIN_API_01",
            user_role="SUPER_ADMIN",
            depot_id="HQ",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Query with Chittagong token: must only see CTG records
            res_ctg = await client.get(
                "/api/v1/auth/scoped-actuals",
                headers={"Authorization": f"Bearer {ctg_token}"},
            )
            assert res_ctg.status_code == 200
            data_ctg = res_ctg.json()
            assert data_ctg["user_depot"] == "CTG"
            assert data_ctg["user_role"] == "DEPOT_MANAGER"
            for record in data_ctg["records"]:
                assert record["depot_id"] == "CTG", f"Non-Chittagong record leaked: {record}"

            # 2. Query with Admin token: sees all depot records
            res_admin = await client.get(
                "/api/v1/auth/scoped-actuals",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert res_admin.status_code == 200
            data_admin = res_admin.json()
            depot_list = [r["depot_id"] for r in data_admin["records"]]
            assert "CTG" in depot_list
            assert "DHK" in depot_list
