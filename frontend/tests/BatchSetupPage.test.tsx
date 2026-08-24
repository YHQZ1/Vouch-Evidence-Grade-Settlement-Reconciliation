import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { BatchSetupPage } from "../src/features/batch/BatchSetupPage";
import { api } from "../src/lib/api";

afterEach(() => vi.restoreAllMocks());

describe("batch setup isolation", () => {
  it("requires an explicit new-batch transition and does not retain source slots", async () => {
    const create = vi.spyOn(api, "createBatch").mockResolvedValueOnce({ batch_id: "batch-1", evaluation_clock: "2026-08-31T18:30:00Z", status: "awaiting_sources", required_sources: ["gateway", "bank", "ledger", "policy"], sources: [], result_available: false, result_batch_id: null, failure: null, created_at: "2026-08-31T18:30:00Z", updated_at: "2026-08-31T18:30:00Z", lifecycle_sequence: 1, links: {} } as never).mockResolvedValueOnce({ batch_id: "batch-2", evaluation_clock: "2026-08-31T18:30:00Z", status: "awaiting_sources", required_sources: ["gateway", "bank", "ledger", "policy"], sources: [], result_available: false, result_batch_id: null, failure: null, created_at: "2026-08-31T18:30:00Z", updated_at: "2026-08-31T18:30:00Z", lifecycle_sequence: 1, links: {} } as never);
    const user = userEvent.setup();
    render(<MemoryRouter><BatchSetupPage /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Create batch" }));
    expect(await screen.findByText(/batch-1 created/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start a new batch" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run reconciliation" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Start a new batch" }));
    expect(screen.queryByRole("heading", { name: "Attach immutable source records" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create batch" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create batch" }));
    expect(await screen.findByText(/batch-2 created/)).toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(2);
  });

  it("keeps an incomplete or failed batch from looking runnable", async () => {
    vi.spyOn(api, "createBatch").mockResolvedValue({ batch_id: "failed-batch", evaluation_clock: "2026-08-31T18:30:00Z", status: "failed", required_sources: ["gateway", "bank", "ledger", "policy"], sources: [], result_available: false, result_batch_id: null, failure: { code: "SOURCE_INVALID", message: "source rejected", sequence: 2 }, created_at: "2026-08-31T18:30:00Z", updated_at: "2026-08-31T18:30:00Z", lifecycle_sequence: 2, links: {} } as never);
    const user = userEvent.setup();
    render(<MemoryRouter><BatchSetupPage /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Create batch" }));
    expect(await screen.findByText(/source rejected/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run reconciliation" })).toBeDisabled();
  });
});
