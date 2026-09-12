import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
    cleanup();
    localStorage.clear();
});

class IntersectionObserverStub implements IntersectionObserver {
    readonly root: Element | Document | null = null;
    readonly rootMargin: string = "";
    readonly scrollMargin: string = "";
    readonly thresholds: ReadonlyArray<number> = [];

    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
        return [];
    }
}

vi.stubGlobal("IntersectionObserver", IntersectionObserverStub);