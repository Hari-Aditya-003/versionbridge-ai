export function discountTotal(subtotal, discount, cap) {
  const deduction = Math.min(subtotal, discount);
  return subtotal - deduction;
}
