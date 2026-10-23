import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";

describe("ChatMarkdown", () => {
  it("renders **bold** text as <strong>", () => {
    render(<ChatMarkdown text="This is **bold** text" />);
    expect(screen.getByText("bold").tagName).toBe("STRONG");
  });

  it("renders `code` text as <code>", () => {
    render(<ChatMarkdown text="Run `npm test` now" />);
    expect(screen.getByText("npm test").tagName).toBe("CODE");
  });

  it("renders *italic* and _italic_ text as <em>", () => {
    render(<ChatMarkdown text="a *star* and an _underscore_ version" />);
    expect(screen.getByText("star").tagName).toBe("EM");
    expect(screen.getByText("underscore").tagName).toBe("EM");
  });

  it("renders a block of '- ' lines as a bulleted list", () => {
    const { container } = render(<ChatMarkdown text={"- first item\n- second item"} />);
    const ul = container.querySelector("ul");
    expect(ul).not.toBeNull();
    expect(ul?.querySelectorAll("li")).toHaveLength(2);
    expect(screen.getByText("first item")).toBeInTheDocument();
    expect(screen.getByText("second item")).toBeInTheDocument();
  });

  it("renders a block of '1. ' lines as a numbered list", () => {
    const { container } = render(<ChatMarkdown text={"1. first step\n2. second step"} />);
    const ol = container.querySelector("ol");
    expect(ol).not.toBeNull();
    expect(ol?.querySelectorAll("li")).toHaveLength(2);
  });

  it("joins single newlines within a paragraph with <br>", () => {
    const { container } = render(<ChatMarkdown text={"line one\nline two"} />);
    const p = container.querySelector("p");
    expect(p).not.toBeNull();
    expect(p?.querySelector("br")).not.toBeNull();
    expect(p?.textContent).toBe("line oneline two");
  });

  it("splits on blank lines into separate paragraphs", () => {
    const { container } = render(<ChatMarkdown text={"first paragraph\n\nsecond paragraph"} />);
    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs).toHaveLength(2);
    expect(paragraphs[0].textContent).toBe("first paragraph");
    expect(paragraphs[1].textContent).toBe("second paragraph");
  });
});
