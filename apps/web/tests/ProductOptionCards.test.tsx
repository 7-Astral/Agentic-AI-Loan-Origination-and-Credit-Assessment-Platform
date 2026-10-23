import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProductOptionCards } from "@/components/chat/ProductOptionCards";
import type { ProductOption } from "@/lib/agent-api";

// Regression coverage for this session's own bug: the discovery turn's
// product cards rendered with their Select button disabled because the
// caller compared against the wrong stage string. interactive=true/false is
// exactly the prop that bug got backwards, so these tests pin its behavior.

const PRODUCTS: ProductOption[] = [
  {
    product_code: "PERSONAL-AAAA1111",
    name: "Personal Loan",
    interest_rate: 9.5,
    comparison_rate: 9.9,
    rate_type: "variable",
    min_amount: 1000,
    max_amount: 50000,
    min_term_months: 6,
    max_term_months: 60,
    features: ["No fees"],
  },
  {
    product_code: "CAR-BBBB2222",
    name: "Car Loan",
    interest_rate: null,
    comparison_rate: null,
    rate_type: null,
    min_amount: 5000,
    max_amount: 80000,
    min_term_months: 12,
    max_term_months: 84,
    features: [],
  },
];

describe("ProductOptionCards", () => {
  it("renders one card per product", () => {
    render(<ProductOptionCards products={PRODUCTS} interactive onSelect={vi.fn()} />);
    expect(screen.getByText("Personal Loan")).toBeInTheDocument();
    expect(screen.getByText("Car Loan")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Select" })).toHaveLength(2);
  });

  it("shows 'Rate on request' when interest_rate is null", () => {
    render(<ProductOptionCards products={PRODUCTS} interactive onSelect={vi.fn()} />);
    expect(screen.getByText("Rate on request")).toBeInTheDocument();
  });

  it("disables the Select buttons when interactive is false", () => {
    render(<ProductOptionCards products={PRODUCTS} interactive={false} onSelect={vi.fn()} />);
    for (const button of screen.getAllByRole("button", { name: "Select" })) {
      expect(button).toBeDisabled();
    }
  });

  it("calls onSelect with the clicked product when interactive is true", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<ProductOptionCards products={PRODUCTS} interactive onSelect={onSelect} />);

    const buttons = screen.getAllByRole("button", { name: "Select" });
    await user.click(buttons[1]);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(PRODUCTS[1]);
  });

  it("does not call onSelect when clicked while not interactive", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<ProductOptionCards products={PRODUCTS} interactive={false} onSelect={onSelect} />);

    const button = screen.getAllByRole("button", { name: "Select" })[0];
    await user.click(button);

    expect(onSelect).not.toHaveBeenCalled();
  });
});
