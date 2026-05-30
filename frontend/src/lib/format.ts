export function dollars(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function points(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}
