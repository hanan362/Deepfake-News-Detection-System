import { act, render, renderHook, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SlowNotice } from "@/components/SlowNotice";
import { useSlowFlag } from "@/hooks/useSlowFlag";
import { SessionCheck } from "@/layouts/guards";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("useSlowFlag", () => {
  it("turns true only after the wait has lasted long enough", () => {
    const { result } = renderHook(() => useSlowFlag(true, 5000));
    expect(result.current).toBe(false);
    act(() => void vi.advanceTimersByTime(4999));
    expect(result.current).toBe(false);
    act(() => void vi.advanceTimersByTime(2));
    expect(result.current).toBe(true);
  });

  it("stays false when the work finishes in time, and resets for the next run", () => {
    const { result, rerender } = renderHook(({ active }) => useSlowFlag(active, 5000), { initialProps: { active: true } });
    act(() => void vi.advanceTimersByTime(3000));
    rerender({ active: false });
    act(() => void vi.advanceTimersByTime(10_000));
    expect(result.current).toBe(false);
    rerender({ active: true });
    act(() => void vi.advanceTimersByTime(6000));
    expect(result.current).toBe(true);
    rerender({ active: false });
    expect(result.current).toBe(false);
  });
});

describe("SlowNotice", () => {
  it("says what is happening and that the result will appear, only when shown", () => {
    const { rerender } = render(<SlowNotice show={false} what="the evidence check" />);
    expect(screen.queryByTestId("slow-notice")).toBeNull();
    rerender(<SlowNotice show what="the evidence check" />);
    expect(screen.getByTestId("slow-notice")).toHaveTextContent(/downloads and loads a model/);
    expect(screen.getByTestId("slow-notice")).toHaveTextContent(/the evidence check/);
  });
});

describe("SessionCheck", () => {
  it("explains a silent server after the wait and offers to try again", () => {
    render(<MemoryRouter><SessionCheck label="Restoring your session" afterMs={8000} /></MemoryRouter>);
    expect(screen.getByText("Restoring your session")).toBeInTheDocument();
    expect(screen.queryByTestId("server-slow")).toBeNull();
    act(() => void vi.advanceTimersByTime(8100));
    expect(screen.getByTestId("server-slow")).toHaveTextContent(/taking a long time to answer/);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
