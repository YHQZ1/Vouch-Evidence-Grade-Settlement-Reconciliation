export function formatSubunits(
  subunits: number | bigint,
  currency = "INR",
): string {
  const value =
    typeof subunits === "number"
      ? (() => {
          if (!Number.isSafeInteger(subunits))
            throw new Error("Unsafe integer currency value received from API");
          return BigInt(subunits);
        })()
      : subunits;
  return formatBigIntSubunits(value, currency);
}

export function formatMonetaryString(
  subunits: string,
  currency = "INR",
): string {
  if (!/^-?\d+$/.test(subunits)) {
    throw new Error(`Invalid monetary value: ${subunits}`);
  }
  return formatBigIntSubunits(BigInt(subunits), currency);
}

function formatBigIntSubunits(value: bigint, currency: string): string {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  const rupees = absolute / 100n;
  const paise = absolute % 100n;
  const digits = rupees.toString();
  const lastThree = digits.slice(-3);
  const rest = digits.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  const grouped = rest ? `${rest},${lastThree}` : lastThree;
  return `${negative ? "-" : ""}${currency} ${grouped}.${paise.toString().padStart(2, "0")}`;
}

export function formatCalculatedValue(name: string, value: string): string {
  return name.endsWith("_subunits") ? formatMonetaryString(value) : value;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function shorten(value: string, visible = 10): string {
  return value.length <= visible * 2
    ? value
    : `${value.slice(0, visible)}…${value.slice(-visible)}`;
}
export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
