import asyncio

import pytest

from alphatrion.utils.context import Context


@pytest.mark.asyncio
async def test_context_no_timeout():
    ctx = Context()
    ctx.start()
    assert not ctx.cancelled()
    ctx.cancel()
    # double cancel should be no-op
    ctx.cancel()
    assert ctx.cancelled()
    await ctx.wait()


@pytest.mark.asyncio
async def test_context_with_timeout():
    ctx = Context(timeout=0.1)
    ctx.start()
    assert not ctx.cancelled()
    await asyncio.sleep(0.2)
    assert ctx.cancelled()
    await ctx.wait()


@pytest.mark.asyncio
async def test_context_manual_cancel():
    ctx = Context(timeout=10000)
    ctx.start()
    assert not ctx.cancelled()
    ctx.cancel()
    assert ctx.cancelled()
    await ctx.wait()


@pytest.mark.asyncio
async def test_context_wait_cancelled():
    ctx = Context()
    ctx.start()

    async def waiter():
        await ctx.wait()
        return True

    task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)
    assert not task.done()
    ctx.cancel()
    result = await task
    assert result is True
    assert ctx.cancelled()


@pytest.mark.asyncio
async def test_context_multiple_waiters():
    ctx = Context()
    ctx.start()
    results = []

    async def waiter(idx):
        await ctx.wait()
        results.append(idx)

    tasks = [asyncio.create_task(waiter(i)) for i in range(5)]
    await asyncio.sleep(0.1)
    assert all(not t.done() for t in tasks)
    ctx.cancel()
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3, 4]
    assert ctx.cancelled()
