import { afterEach, describe, expect, it, vi } from "vitest";
import { api, downloadExport } from "../src/lib/api";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("typed API pagination and exports", () => {
  it("does not send a browser-selected limit and follows every settlement page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const offset = new URL(url, "http://localhost").searchParams.get("offset");
      const body = offset === "0" ? { batch_id: "b", items: [{ aggregate: { settlement_id: "s1" } }], total: 2, offset: 0, limit: 1, next_offset: 1 } : { batch_id: "b", items: [{ aggregate: { settlement_id: "s2" } }], total: 2, offset: 1, limit: 1, next_offset: null };
      return Promise.resolve({ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: () => Promise.resolve(body) } as Response);
    });
    vi.stubGlobal("fetch", fetchMock);
    const result = await api.listSettlements("b");
    expect(result.items.map((item) => item.aggregate.settlement_id)).toEqual(["s1", "s2"]);
    expect(fetchMock.mock.calls.map(([input]) => String(input))).toEqual(["/api/v1/batches/b/settlements?offset=0", "/api/v1/batches/b/settlements?offset=1"]);
  });

  it("follows complete exception and audit collections independently", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const parsed = new URL(url, "http://localhost");
      const resource = parsed.pathname.split("/").at(-1);
      const offset = parsed.searchParams.get("offset");
      const body = resource === "exceptions"
        ? offset === "0"
          ? { batch_id: "b", items: [{ exception_id: "e1" }], total: 2, offset: 0, limit: 1, next_offset: 1 }
          : { batch_id: "b", items: [{ exception_id: "e2" }], total: 2, offset: 1, limit: 1, next_offset: null }
        : offset === "0"
          ? { batch_id: "b", items: [{ audit_id: "a1" }], total: 2, offset: 0, limit: 1, next_offset: 1 }
          : { batch_id: "b", items: [{ audit_id: "a2" }], total: 2, offset: 1, limit: 1, next_offset: null };
      return Promise.resolve({ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: () => Promise.resolve(body) } as Response);
    });
    vi.stubGlobal("fetch", fetchMock);
    const exceptions = await api.listExceptions("b");
    const audit = await api.listAudit("b");
    expect(exceptions.items.map((item) => item.exception_id)).toEqual(["e1", "e2"]);
    expect(audit.items.map((item) => item.audit_id)).toEqual(["a1", "a2"]);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it.each([
    ["reconciliation-result", "frozen-result.json"],
    ["exceptions", "frozen-exceptions.json"],
    ["audit-events", "frozen-audit.json"],
  ] as const)("downloads the server filename for %s", async (artifact, filename) => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, status: 200, headers: new Headers({ "content-disposition": `attachment; filename=\"${filename}\"` }), blob: () => Promise.resolve(new Blob(["{}"], { type: "application/json" })) } as Response)));
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:test"), revokeObjectURL: vi.fn() });
    const downloaded = await downloadExport("b", artifact);
    expect(downloaded).toBe(filename);
    expect(click).toHaveBeenCalledOnce();
    await new Promise((resolve) => window.setTimeout(resolve, 0));
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test");
  });
});
