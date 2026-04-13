"""API-Routen für Anzeigen."""

import logging
from typing import Any

import anyio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Row, and_
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlmodel import Session, col, func, select

from app.core.auth import CurrentUser, get_current_user
from app.core.db import apply_api_statement_timeout_sync, db_engine
from app.core.debug_runtime import write_debug_log
from app.core.request_context import get_http_request_trace_id
from app.models.ad import Ad, AdRead

router = APIRouter(prefix="/ads", tags=["Ads"])
_log = logging.getLogger("schnappster.ads")

# Debug c4423a: Logs zeigten Haenger nur nach COUNT, bei „before page SELECT“ (H19a ohne H19).
# Zwei kurze Sessions (COUNT dann Page): Transaktion/Cursor zwischen den Executes schliessen,
# statt zwei Statements in derselben offenen Session auf einer gepoolten Tx-Pooler-Verbindung.
_AD_LIST_COLUMNS = (
    Ad.id,
    Ad.owner_id,
    Ad.adsearch_id,
    Ad.external_id,
    Ad.title,
    Ad.description,
    Ad.price,
    Ad.postal_code,
    Ad.city,
    Ad.url,
    Ad.image_urls,
    Ad.condition,
    Ad.shipping_cost,
    Ad.seller_name,
    Ad.seller_url,
    Ad.seller_rating,
    Ad.seller_is_friendly,
    Ad.seller_is_reliable,
    Ad.seller_type,
    Ad.seller_active_since,
    Ad.bargain_score,
    Ad.ai_summary,
    Ad.ai_reasoning,
    Ad.is_analyzed,
    Ad.first_seen_at,
)


def _ad_row_to_read(row: Row[Any]) -> AdRead:
    m = dict(row._mapping)
    m.pop("_list_total", None)
    return AdRead.model_validate(m)


def _ads_trace(message: str) -> None:
    if _log.isEnabledFor(logging.DEBUG):
        rid = get_http_request_trace_id() or "-"
        _log.debug("[%s] ads %s", rid, message)


def _fetch_list_ads_sync(
    user_id: str,
    adsearch_id: int | None,
    is_analyzed: bool | None,
    min_score: int | None,
    sort: str,
    limit: int,
    offset: int,
) -> dict[str, object]:
    conditions: list[Any] = [Ad.owner_id == user_id]
    if adsearch_id is not None:
        conditions.append(Ad.adsearch_id == adsearch_id)
    if is_analyzed is not None:
        conditions.append(Ad.is_analyzed == is_analyzed)
    if min_score is not None and min_score > 0:
        conditions.append(col(Ad.bargain_score) >= min_score)

    where_clause = and_(*conditions)
    count_stmt = select(func.count()).select_from(Ad).where(where_clause)

    order = {
        "date": col(Ad.first_seen_at).desc(),
        "price-asc": col(Ad.price).asc(),
        "price-desc": col(Ad.price).desc(),
        "score-desc": col(Ad.bargain_score).desc(),
    }
    page_stmt = (
        select(*_AD_LIST_COLUMNS)  # type: ignore[call-overload]
        .where(where_clause)
        .order_by(order.get(sort, col(Ad.first_seen_at).desc()))
        .offset(offset)
        .limit(min(limit, 100))
    )

    with Session(db_engine) as session:
        apply_api_statement_timeout_sync(session)
        # region agent log
        write_debug_log(
            run_id="ads-hang",
            hypothesis_id="H17",
            location="app/routes/api/ads.py:_fetch_list_ads_sync",
            message="count session: after SET LOCAL",
            data={},
        )
        write_debug_log(
            run_id="ads-hang",
            hypothesis_id="H19count",
            location="app/routes/api/ads.py:_fetch_list_ads_sync",
            message="before COUNT",
            data={},
        )
        # endregion
        total = int(session.exec(count_stmt).one())
        # region agent log
        write_debug_log(
            run_id="ads-hang",
            hypothesis_id="H22",
            location="app/routes/api/ads.py:_fetch_list_ads_sync",
            message="after COUNT",
            data={"total": total},
        )
        # endregion
    # region agent log
    write_debug_log(
        run_id="ads-hang",
        hypothesis_id="H23",
        location="app/routes/api/ads.py:_fetch_list_ads_sync",
        message="count session closed (checkout returned)",
        data={"total": total},
    )
    # endregion

    with Session(db_engine) as session:
        apply_api_statement_timeout_sync(session)
        # region agent log
        write_debug_log(
            run_id="ads-hang",
            hypothesis_id="H20",
            location="app/routes/api/ads.py:_fetch_list_ads_sync",
            message="page session: after SET LOCAL",
            data={},
        )
        write_debug_log(
            run_id="ads-hang",
            hypothesis_id="H19a",
            location="app/routes/api/ads.py:_fetch_list_ads_sync",
            message="before page SELECT",
            data={},
        )
        # endregion
        rows = session.execute(page_stmt).all()
    # region agent log
    write_debug_log(
        run_id="ads-hang",
        hypothesis_id="H19",
        location="app/routes/api/ads.py:_fetch_list_ads_sync",
        message="after page SELECT",
        data={"n_items": len(rows)},
    )
    # endregion

    items = [_ad_row_to_read(r) for r in rows]
    return {"items": items, "total": total}


def _fetch_one_ad_read_sync(session: Session, user_id: str, ad_id: int) -> AdRead | None:
    apply_api_statement_timeout_sync(session)
    q = select(*_AD_LIST_COLUMNS).where(Ad.id == ad_id, Ad.owner_id == user_id)  # type: ignore[call-overload]
    row = session.execute(q).first()
    if row is None:
        return None
    return _ad_row_to_read(row)


def _list_ads_in_thread(
    user_id: str,
    adsearch_id: int | None,
    is_analyzed: bool | None,
    min_score: int | None,
    sort: str,
    limit: int,
    offset: int,
) -> dict[str, object]:
    # region agent log
    write_debug_log(
        run_id="ads-hang",
        hypothesis_id="H16",
        location="app/routes/api/ads.py:_list_ads_in_thread",
        message="thread entered",
        data={},
    )
    # endregion
    return _fetch_list_ads_sync(
        user_id,
        adsearch_id,
        is_analyzed,
        min_score,
        sort,
        limit,
        offset,
    )


def _get_ad_in_thread(user_id: str, ad_id: int) -> AdRead | None:
    with Session(db_engine) as session:
        return _fetch_one_ad_read_sync(session, user_id, ad_id)


# --------------
# --- Routen ---
# --------------
@router.get("/")
async def list_ads(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    adsearch_id: int | None = None,
    is_analyzed: bool | None = None,
    min_score: int | None = None,
    sort: str = "date",
    limit: int = 24,
    offset: int = 0,
):
    """Gibt paginierte Anzeigen mit optionalen Filtern
    (adsearch_id, is_analyzed, min_score) und Sortierung zurück.
    """

    _ads_trace("list_ads threadpool start")
    # region agent log
    write_debug_log(
        run_id="ads-hang",
        hypothesis_id="H15",
        location="app/routes/api/ads.py:list_ads",
        message="before to_thread",
        data={"rid": get_http_request_trace_id() or "-"},
    )
    # endregion
    try:
        out = await anyio.to_thread.run_sync(
            _list_ads_in_thread,
            current_user.user_id,
            adsearch_id,
            is_analyzed,
            min_score,
            sort,
            limit,
            offset,
        )
    except SATimeoutError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database pool busy — retry shortly",
        ) from exc
    _ads_trace("list_ads threadpool done")
    # region agent log
    write_debug_log(
        run_id="ads-hang",
        hypothesis_id="H15b",
        location="app/routes/api/ads.py:list_ads",
        message="after to_thread ok",
        data={"rid": get_http_request_trace_id() or "-"},
    )
    # endregion
    return out


@router.get("/{ad_id}", response_model=AdRead)
async def get_ad(
    ad_id: int,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt eine Anzeige anhand der ID zurück; 404 wenn nicht gefunden."""

    _ads_trace("get_ad threadpool start")
    try:
        ad_read = await anyio.to_thread.run_sync(
            _get_ad_in_thread,
            current_user.user_id,
            ad_id,
        )
    except SATimeoutError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database pool busy — retry shortly",
        ) from exc
    _ads_trace("get_ad threadpool done")
    if not ad_read:
        raise HTTPException(status_code=404, detail="Ad not found")
    return ad_read
