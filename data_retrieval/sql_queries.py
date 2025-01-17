# Description: SQL queries for data retrieval


MAKE_READY_QUERY = """

DECLARE @CalendarDate DATE = DATEADD(DAY, -1, GETDATE());
DECLARE @StartDate DATE = DATEADD(DAY, -29, @CalendarDate);

WITH ActiveProperties AS (
    SELECT DISTINCT
        PropertyKey,
        PropertyName
    FROM dbo.DimProperty
    WHERE PropertyStatus = 'ACTIVE'
        AND IsDeleted = 'N'
        AND RowIsCurrent = 'Y'
        AND PropertyName NOT LIKE 'Historical%'
),

WorkOrderMetrics AS (
    SELECT
        p.PropertyKey,
        p.PropertyName,

        -- Open Work Orders (carried over from before start date)
        SUM(CASE
            WHEN wo.CancelDate IS NULL
            AND CAST(wo.CreateDate AS DATE) < @StartDate
            AND (wo.ActualCompletedDate IS NULL
                 OR CAST(wo.ActualCompletedDate AS DATE) >= @StartDate)
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            AND wo.StatusCode NOT IN (3)
            THEN 1
            ELSE 0
        END) AS OpenWorkOrder_Current,

        -- Actual Open Work Orders (created in last 30 days)
        SUM(CASE
            WHEN CAST(wo.CreateDate AS DATE) >= @StartDate
            AND wo.StatusCode NOT IN (3)
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            THEN 1
            ELSE 0
        END) AS ActualOpenWorkOrders_Current,

        -- Completed Work Orders (only count completions of work orders that were either open at start or created during period)
        SUM(CASE
            WHEN CAST(wo.ActualCompletedDate AS DATE) BETWEEN @StartDate AND @CalendarDate
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            AND wo.StatusCode = 4
            AND (
                -- Was open at start date
                (CAST(wo.CreateDate AS DATE) < @StartDate)
                OR
                -- Was created during period
                (CAST(wo.CreateDate AS DATE) >= @StartDate)
            )
            THEN 1
            ELSE 0
        END) AS CompletedWorkOrder_Current,

        -- Cancelled Work Orders (only count cancellations of work orders that were either open at start or created during period)
        SUM(CASE
            WHEN wo.CancelDate IS NOT NULL
            AND CAST(wo.CancelDate AS DATE) BETWEEN @StartDate AND @CalendarDate
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            AND wo.StatusCode = 3
            AND (
                -- Was open at start date
                (CAST(wo.CreateDate AS DATE) < @StartDate)
                OR
                -- Was created during period
                (CAST(wo.CreateDate AS DATE) >= @StartDate)
            )
            THEN 1
            ELSE 0
        END) AS CancelledWorkOrder_Current,

        -- Days to Complete
        SUM(CASE
            WHEN (wo.CancelDate IS NULL OR wo.CancelDate < wo.ActualCompletedDate)
            AND CAST(wo.ActualCompletedDate AS DATE)
                BETWEEN @StartDate AND @CalendarDate
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            AND wo.StatusCode = 4
            THEN
                CASE
                    WHEN wo.ExcludeWeekEndDaysCount > 0
                    THEN (wo.WOActualWorkMinutes / 1440.0) - wo.ExcludeWeekEndDaysCount
                    ELSE wo.WOActualWorkMinutes / 1440.0
                END
            ELSE 0
        END) AS TotalDaysToComplete,

        -- Count completed orders for average calculation
        SUM(CASE
            WHEN CAST(wo.ActualCompletedDate AS DATE)
                BETWEEN @StartDate AND @CalendarDate
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            AND wo.StatusCode = 4
            THEN 1
            ELSE 0
        END) AS CompletedOrderCount,

        -- Currently Open Work Orders (for accurate pending calculation)
        SUM(CASE
            WHEN wo.CancelDate IS NULL
            AND wo.ActualCompletedDate IS NULL
            AND wo.IsDeleted = 'N'
            AND wo.RowIsCurrent = 'Y'
            AND wo.StatusCode NOT IN (3, 4)
            THEN 1
            ELSE 0
        END) AS CurrentlyOpenWorkOrders
    FROM ActiveProperties p
    LEFT JOIN dbo.DimWorkOrder wo ON p.PropertyKey = wo.PropertyKey
    WHERE wo.MakeReadyFlag = 0
        AND wo.IsDeleted = 'N'
        AND wo.RowIsCurrent = 'Y'
    GROUP BY
        p.PropertyKey,
        p.PropertyName
)

SELECT
    wm.PropertyKey,
    wm.PropertyName,
    dp.PropertyStateProvinceCode,
    dp.PropertyCity,
    fo.TotalUnitCount,

    wm.OpenWorkOrder_Current,
    wm.ActualOpenWorkOrders_Current,
    wm.CancelledWorkOrder_Current,
    wm.CompletedWorkOrder_Current,

    -- Pending Work Orders (using currently open work orders)
    wm.CurrentlyOpenWorkOrders AS PendingWorkOrders,

    -- Average Days to Complete
    CASE
        WHEN wm.CompletedOrderCount > 0
        THEN ROUND(wm.TotalDaysToComplete / wm.CompletedOrderCount, 1)
        ELSE 0
    END AS AverageDaysToComplete,

    -- Percentage Completed
    CASE
        WHEN (wm.OpenWorkOrder_Current + wm.ActualOpenWorkOrders_Current) > 0
        THEN ROUND(
            (CAST(wm.CompletedWorkOrder_Current AS FLOAT) * 100.0) /
            (wm.OpenWorkOrder_Current + wm.ActualOpenWorkOrders_Current), 1)
        ELSE 0
    END AS PercentageCompletedThisPeriod,

    @StartDate AS PeriodStartDate,
    @CalendarDate AS PeriodEndDate,
    fo.PostDate AS LatestPostDate

FROM WorkOrderMetrics wm
LEFT JOIN dbo.FactOperationalKPI fo ON wm.PropertyKey = fo.PropertyKey
LEFT JOIN dbo.DimProperty dp ON wm.PropertyKey = dp.PropertyKey 
    AND dp.RowIsCurrent = 'Y' 
    AND dp.IsDeleted = 'N'
ORDER BY wm.PropertyName;

"""

VERSION_CHECK_QUERY = """
         SELECT 
            MAX(PostDate) as last_modified,
            COUNT(DISTINCT PropertyKey) as record_count
        FROM dbo.FactOperationalKPI
        WHERE PropertyKey IN (
            SELECT DISTINCT PropertyKey 
            FROM dbo.DimProperty 
            WHERE PropertyStatus = 'ACTIVE'
                AND IsDeleted = 'N'
                AND RowIsCurrent = 'Y'
                AND PropertyName NOT LIKE 'Historical%'
         )
"""
