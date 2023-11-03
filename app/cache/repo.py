import uuid

from app.cache.client import AsyncRedisClient
from app.cache.key_gen import KeyGen
from app.core.config import settings
from app.schemas import OTPSaltedHashClaim, RefreshTokenClaim, TokenBase


class CacheRepo:
    """Cache repo"""

    async def save_token_claim(
        self,
        rc: AsyncRedisClient,
        *,
        key: uuid.UUID | str,
        token_claim: TokenBase,
        keep_ttl: bool = False,
    ) -> bool:
        """
        Cache token claim.

        The token claim is cached for its corresponding ttl.

        If the keep_ttl is set to True, the ttl is not changed when the token is updated.
        However if the token is not found in the cache, the ttl is set to the token's ttl.

        Returns:
            bool: True if successful, False otherwise.
        """
        key_gen = KeyGen.from_token(type(token_claim))
        key = key_gen(key)

        if keep_ttl:
            rt_exists = await rc.exists(key)
            if rt_exists:
                return await rc.set(key, token_claim, keepttl=True)

        ttl = self._get_token_ttl(type(token_claim))

        return await rc.set(key, token_claim, ttl=ttl)

    async def get_token[T: TokenBase](
        self,
        rc: AsyncRedisClient,
        *,
        key: uuid.UUID | str,
        token_cls: type[T],
    ) -> T | None:
        """Get token claim"""
        key_gen = KeyGen.from_token(token_cls)
        key = key_gen(key)
        token = await rc.get(key)
        return token_cls.model_validate(token) if token else None

    async def delete_token(
        self,
        rc: AsyncRedisClient,
        *,
        key: uuid.UUID | str,
        key_gen: KeyGen,
    ) -> bool:
        """Delete token claim from redis"""
        key = key_gen(key)
        return await rc.delete(key)

    def _get_token_ttl(self, token_cls: type[TokenBase]) -> int:
        ttl = {
            RefreshTokenClaim: settings.REFRESH_TOKEN_EXPIRE_SECONDS,
            OTPSaltedHashClaim: settings.OTP_EXPIRE_SECONDS,
        }.get(token_cls, None)

        if ttl is None:
            raise ValueError(f"Invalid token type: {token_cls}")

        return ttl


repo = CacheRepo()
