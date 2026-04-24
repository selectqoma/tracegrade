import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = `/api/${path.join("/")}`;

  const body = await request.json();
  const res = await fetch(`${API_URL}${apiPath}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": process.env.TRACEGRADE_API_KEY || "dev",
    },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = `/api/${path.join("/")}`;
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_URL}${apiPath}${searchParams ? `?${searchParams}` : ""}`;

  const res = await fetch(url, {
    headers: {
      "X-API-Key": process.env.TRACEGRADE_API_KEY || "dev",
    },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = `/api/${path.join("/")}`;

  const res = await fetch(`${API_URL}${apiPath}`, {
    method: "DELETE",
    headers: {
      "X-API-Key": process.env.TRACEGRADE_API_KEY || "dev",
    },
  });

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
